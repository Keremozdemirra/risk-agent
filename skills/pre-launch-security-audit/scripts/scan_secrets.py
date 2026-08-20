#!/usr/bin/env python3
"""Mechanical first pass for the pre-launch security audit.

Catches the pattern-matchable subset of the 23-item checklist fast, so the
audit can spend its attention on the parts that need reading code: auth,
authorization, and data access.

Usage:
    python3 scan_secrets.py [project_dir]

Exit code is 1 if anything CRITICAL was found, else 0 (useful in CI).
Every finding is a *candidate* — verify each one in the file before reporting
it to the user. False positives here are expected and cheap; a missed hole is
not.
"""

import json
import os
import re
import subprocess
import sys
from collections import defaultdict

SKIP_DIRS = {
    ".git", "node_modules", ".next", "dist", "build", "out", ".venv", "venv",
    "__pycache__", ".turbo", ".cache", "coverage", ".pytest_cache", "vendor",
    ".svelte-kit", ".nuxt", "target",
}
# Build output is scanned separately and deliberately: a secret reaching these
# directories is already public, which is a strictly worse finding.
BUILD_DIRS = {"dist", "build", ".next", "out", ".svelte-kit", ".nuxt"}

TEXT_EXT = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".rb", ".go", ".php",
    ".java", ".kt", ".rs", ".svelte", ".vue", ".astro", ".html", ".json",
    ".yml", ".yaml", ".toml", ".env", ".sh", ".sql", ".md", ".txt", ".tf",
}

# (label, regex, severity)
SECRET_PATTERNS = [
    ("OpenAI secret key",        r"sk-[A-Za-z0-9_-]{20,}",                  "CRITICAL"),
    ("Anthropic API key",        r"sk-ant-[A-Za-z0-9_-]{20,}",              "CRITICAL"),
    ("Stripe secret/restricted", r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{20,}", "CRITICAL"),
    ("Supabase service_role",    r"service_role",                           "CRITICAL"),
    ("AWS access key id",        r"\bAKIA[0-9A-Z]{16}\b",                   "CRITICAL"),
    ("Google API key",           r"\bAIza[0-9A-Za-z_-]{35}\b",              "CRITICAL"),
    ("GitHub token",             r"\bgh[pousr]_[A-Za-z0-9]{36,}",           "CRITICAL"),
    ("Slack token",              r"\bxox[baprs]-[A-Za-z0-9-]{10,}",         "CRITICAL"),
    ("SendGrid key",             r"\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}", "CRITICAL"),
    ("Private key block",        r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----", "CRITICAL"),
    ("JWT literal",              r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "HIGH"),
    ("Twilio account sid",       r"\bAC[a-f0-9]{32}\b",                     "HIGH"),
    ("Generic hardcoded secret", r"(?i)(?:api[_-]?key|secret|password|passwd|token)\s*[:=]\s*['\"][A-Za-z0-9_\-!@#$%^&*+/=]{12,}['\"]", "HIGH"),
    ("Client-exposed env var",   r"\b(?:VITE_|NEXT_PUBLIC_|REACT_APP_|PUBLIC_|EXPO_PUBLIC_)[A-Z0-9_]*(?:SECRET|SERVICE|PRIVATE|TOKEN|PASSWORD|SERVICE_ROLE)[A-Z0-9_]*", "CRITICAL"),
]

CODE_PATTERNS = [
    ("Raw HTML injection (XSS)",     r"dangerouslySetInnerHTML|\.innerHTML\s*=|v-html|\{@html|\|\s*safe\b|mark_safe\(", "HIGH"),
    ("eval / dynamic code",          r"\beval\(|new Function\(|exec\(", "MEDIUM"),
    # Backtick template literal containing SQL and an interpolation
    ("Interpolated SQL (template)",  r"(?is)(?:query|execute|raw|queryRawUnsafe|prepare|all|get|run)\s*\(\s*`[^`]{0,400}?\b(?:select|insert\s+into|update|delete\s+from)\b[^`]{0,400}?\$\{", "CRITICAL"),
    # Quoted SQL string glued to a variable with +, or %-/format-interpolated
    ("Interpolated SQL (concat)",    r"(?is)(?:query|execute|raw|queryRawUnsafe|cursor\.execute)\s*\(\s*(?:f?['\"][^'\"]{0,400}?\b(?:select|insert\s+into|update|delete\s+from)\b[^'\"]{0,400}?['\"]\s*(?:\+|%)|f['\"][^'\"]{0,400}?\{)", "CRITICAL"),
    ("Wildcard / reflected CORS",    r"Access-Control-Allow-Origin[\"']?\s*[:,]\s*[\"']\*|origin\s*:\s*(?:true|[\"']\*[\"'])|origin\s*:\s*req\.headers\.origin", "HIGH"),
    # md5(password) / sha256(pwd) / createHash('sha256').update(password) / hashlib.sha1(pw)
    ("Weak password hash",           r"(?i)(?:\b(?:md5|sha1|sha256|sha512)\s*\(\s*[^)]{0,40}(?:pass|pwd)|createHash\s*\(\s*['\"](?:md5|sha1|sha256|sha512)['\"][^;\n]{0,80}(?:pass|pwd)|hashlib\.(?:md5|sha1|sha256)\s*\([^)]{0,40}(?:pass|pwd))", "CRITICAL"),
    ("Token in localStorage",        r"localStorage\.setItem\(\s*['\"][^'\"]*(?:token|jwt|session|auth)", "HIGH"),
    ("Cookie without httpOnly",      r"(?s)(?:res\.cookie|cookies\.set)\([^)]{0,300}?\)", "REVIEW"),
    ("Error detail returned",        r"(?:err|error|e)\.(?:stack|message)\s*\}?\s*(?:,|\)|\})", "MEDIUM"),
    ("TLS verification disabled",    r"rejectUnauthorized\s*:\s*false|verify\s*=\s*False|NODE_TLS_REJECT_UNAUTHORIZED", "HIGH"),
    ("Debug mode on",                r"DEBUG\s*=\s*True|debug\s*:\s*true", "MEDIUM"),
    ("Whole-object logging",         r"console\.(?:log|error|info)\(\s*(?:req\.body|req\.headers|user|session|event|payload)\b|print\(\s*(?:request\.\w+|user|payload)\b", "MEDIUM"),
    ("Permissive RLS policy",        r"(?i)using\s*\(\s*true\s*\)|with\s+check\s*\(\s*true\s*\)|allow\s+read,\s*write\s*:\s*if\s+true", "CRITICAL"),
]

RATE_LIMIT_HINTS = r"rate[-_]?limit|ratelimit|throttle|slow-?down|limiter|Ratelimit"
VALIDATION_HINTS = r"\bfrom\s+['\"](?:zod|yup|valibot|joi)['\"]|require\(['\"](?:zod|yup|valibot|joi)['\"]\)|from pydantic|BaseModel"
WEBHOOK_FILE = r"webhook|callback"
WEBHOOK_VERIFY = r"constructEvent|verifyHeader|createHmac|timingSafeEqual|verify_signature|Webhook\("
HEADER_HINTS = (r"helmet|Strict-Transport-Security|Content-Security-Policy|"
                r"X-Content-Type-Options|X-Frame-Options|Referrer-Policy|"
                r"headers\s*\(\s*\)|secure_headers")

findings = defaultdict(list)


def add(sev, label, where, detail=""):
    findings[sev].append((label, where, detail))


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        rel_parts = set(os.path.relpath(dirpath, root).split(os.sep))
        in_build = bool(rel_parts & BUILD_DIRS)
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS or (d in BUILD_DIRS and dirpath == root)
        ]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in TEXT_EXT and not fn.startswith(".env"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(path) > 3_000_000:
                    continue
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            yield path, os.path.relpath(path, root), text, in_build


def scan_files(root):
    example_env = re.compile(r"\.env\.(?:example|sample|template)$|\.example$")
    for path, rel, text, in_build in walk(root):
        is_example = bool(example_env.search(rel))
        lines = text.splitlines()

        for label, pat, sev in SECRET_PATTERNS:
            for m in re.finditer(pat, text):
                line_no = text.count("\n", 0, m.start()) + 1
                snippet = lines[line_no - 1].strip()[:120] if line_no <= len(lines) else ""
                if is_example and not re.search(r"[A-Za-z0-9]{24,}", snippet):
                    continue  # placeholder in an .env.example
                if re.search(r"(?i)your[-_]?|xxx|placeholder|example|<[a-z_]+>|\.\.\.", snippet):
                    continue
                note = "IN BUILD OUTPUT — already public" if in_build else ""
                add(sev, label, f"{rel}:{line_no}", (note + " " + snippet).strip())

        if rel.endswith((".md", ".txt")):
            continue
        for label, pat, sev in CODE_PATTERNS:
            for m in re.finditer(pat, text):
                line_no = text.count("\n", 0, m.start()) + 1
                snippet = lines[line_no - 1].strip()[:120] if line_no <= len(lines) else ""
                if label == "Cookie without httpOnly":
                    if "httpOnly" in m.group(0) and "secure" in m.group(0).lower():
                        continue
                    add("HIGH", "Cookie may lack httpOnly/secure/sameSite",
                        f"{rel}:{line_no}", snippet)
                    continue
                add(sev, label, f"{rel}:{line_no}", snippet)


def scan_git(root):
    def git(*args):
        try:
            return subprocess.run(
                ["git", "-C", root, *args],
                capture_output=True, text=True, timeout=30
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""

    if not os.path.isdir(os.path.join(root, ".git")):
        add("INFO", "Not a git repository", ".", "skipped history checks")
        return

    tracked = [l for l in git("ls-files").splitlines()
               if re.search(r"(^|/)\.env", l)
               and not re.search(r"\.(example|sample|template)$", l)]
    for t in tracked:
        add("CRITICAL", ".env is tracked in git", t, "rotate keys, untrack, gitignore")

    hist = git("log", "--all", "--full-history", "--oneline", "--", "*.env", "*.env.*")
    if hist:
        n = len(hist.splitlines())
        add("CRITICAL", ".env appears in git history", f"{n} commit(s)",
            "removing the file later does not remove it from history — rotate every key")

    gi_path = os.path.join(root, ".gitignore")
    gi = open(gi_path, encoding="utf-8", errors="ignore").read() if os.path.exists(gi_path) else ""
    if not re.search(r"^\s*\.env", gi, re.M):
        add("HIGH", ".gitignore does not cover .env", ".gitignore" if gi else "(missing)")


# Does this project accept requests from the network at all? The absence-of-thing
# checks below (rate limiting, request validation, security headers) only mean
# something if it does. Reporting "no rate limiting" on a pure library or CLI is
# noise, and noise is what makes an audit stop being read.
# Framework names are matched only in import/dependency position — a bare word
# match is wrong (Python's builtin next() made every library look like a server).
WEB_SURFACE = (
    # JS/TS: import or require of a server framework
    r"""(?:from|require)\s*\(?\s*['"](?:express|fastify|koa|hapi|next|next/[\w/]+|"""
    r"""nuxt|remix|hono|@sveltejs/kit|@nestjs/[\w-]+)['"]|"""
    # package.json dependency entry
    r'"(?:express|fastify|koa|hapi|next|nuxt|remix|hono|@sveltejs/kit|@nestjs/core)"\s*:|'
    # Python: import of a web framework, or a pinned requirement
    r"(?:^|\n)\s*(?:from|import)\s+(?:fastapi|flask|django|starlette|sanic|tornado|"
    r"bottle|aiohttp\.web|quart|falcon)\b|"
    r"(?:^|\n)\s*(?:fastapi|flask|django|starlette|sanic|tornado|quart)\s*[=>~]=|"
    # route and server definitions, in any language
    r"createServer\s*\(|app\.(?:get|post|put|patch|delete|use)\s*\(|"
    r"router\.(?:get|post|put|patch|delete)\s*\(|"
    r"@(?:app|router|bp)\.(?:route|get|post|put|delete)\b|urlpatterns\s*=|"
    r"export\s+(?:async\s+)?function\s+(?:GET|POST|PUT|PATCH|DELETE)\s*\(|"
    r"\bnet/http\b|\bgin\.(?:Default|New)\(|\bactix_web::|\baxum::"
)


def scan_project_shape(root):
    """Absence-of-thing checks: rate limiting, validation, headers, webhooks."""
    joined, files = [], []
    for path, rel, text, in_build in walk(root):
        if in_build or rel.endswith((".md", ".txt")):
            continue
        files.append(rel)
        joined.append(text)
    blob = "\n".join(joined)

    has_web = bool(re.search(WEB_SURFACE, blob, re.I))
    if not has_web:
        add("INFO", "No HTTP surface detected", "project-wide",
            "skipped rate-limiting, request-validation and security-header checks — "
            "they do not apply to a library or CLI. If this project does serve "
            "requests, say so and re-check those three by hand.")
    else:
        if not re.search(RATE_LIMIT_HINTS, blob):
            add("HIGH", "No rate limiting found anywhere", "project-wide",
                "login, signup, password reset and paid-API routes are unthrottled")
        if not re.search(VALIDATION_HINTS, blob):
            add("HIGH", "No schema validation library in use", "project-wide",
                "request bodies appear to be trusted as-is")
        if not re.search(HEADER_HINTS, blob):
            add("MEDIUM", "No security headers configured", "project-wide",
                "no CSP / HSTS / nosniff found in config or middleware")

    for rel, text in zip(files, joined):
        if re.search(WEBHOOK_FILE, rel, re.I) and not re.search(WEBHOOK_VERIFY, text):
            add("CRITICAL", "Webhook handler without signature verification", rel,
                "unauthenticated write endpoint")

    pkg = os.path.join(root, "package.json")
    if os.path.exists(pkg):
        try:
            data = json.load(open(pkg, encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            add("INFO", f"{len(deps)} npm dependencies", "package.json",
                "run: npm audit --omit=dev")
        except (OSError, ValueError):
            pass
        has_lock = any(os.path.exists(os.path.join(root, f)) for f in
                       ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb"))
        if not has_lock:
            add("MEDIUM", "No lockfile committed", ".",
                "dependency versions are not reproducible")


ORDER = ["CRITICAL", "HIGH", "MEDIUM", "REVIEW", "INFO"]


def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    scan_files(root)
    scan_git(root)
    scan_project_shape(root)

    print(f"\n=== Security scan: {root} ===")
    total = 0
    for sev in ORDER:
        items = findings.get(sev)
        if not items:
            continue
        seen, deduped = set(), []
        for label, where, detail in items:
            key = (label, where)
            if key in seen:
                continue
            seen.add(key)
            deduped.append((label, where, detail))
        print(f"\n-- {sev} ({len(deduped)}) --")
        for label, where, detail in deduped[:60]:
            print(f"  [{label}] {where}")
            if detail:
                print(f"      {detail}")
        if len(deduped) > 60:
            print(f"  ... and {len(deduped) - 60} more")
        if sev not in ("INFO",):
            total += len(deduped)

    print(f"\n{total} actionable candidate(s). Verify each in the file before reporting.")
    print("Pattern matching cannot see missing authorization, IDOR, or broken RLS —")
    print("read the auth and data-access code, then do item 23 (attack it yourself).")
    return 1 if findings.get("CRITICAL") else 0


if __name__ == "__main__":
    sys.exit(main())
