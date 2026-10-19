#!/usr/bin/env node
// CI doctrine guard — locus-evolution-lab private/standards/CI-DOCTRINE.md (lab e3d6f84).
// Reads every workflow in .github/workflows and fails on any of:
//   - an action or reusable workflow not pinned to a 40-character SHA with a "# version" comment
//   - a service or job container image without an @sha256 digest
//   - top-level `permissions:` missing, or granting write (widen per job instead)
//   - pull_request_target together with a checkout of the PR head
//   - a stored secret read by a job that a pull_request event can start (unless the job
//     carries "# exception: secret-on-pr owner: <who> until: <YYYY-MM-DD> — reason")
//   - a secret missing from docs/security/secret-inventory.md
//   - a `ci-green` aggregator that is not if: always(), does not check for success,
//     or does not need every other job in its file (except jobs named on a
//     "# not gating: a, b — reason" comment inside it); no aggregator at all
//   - continue-on-error without "owner: <who> until: <YYYY-MM-DD>", or past that date
//   - a download from releases/latest
// Findings carry file, line and rule only. Usage: node check-workflow-doctrine.mjs [repo-root]
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.argv[2] ?? ".";
const dir = join(root, ".github", "workflows");
const inventoryPath = join(root, "docs", "security", "secret-inventory.md");
const inventory = existsSync(inventoryPath) ? readFileSync(inventoryPath, "utf8") : "";
const today = new Date().toISOString().slice(0, 10);
const problems = [];
const fail = (file, line, rule) => problems.push(`${file}:${line}: ${rule}`);

const files = existsSync(dir) ? readdirSync(dir).filter((f) => /\.ya?ml$/.test(f)).sort() : [];
if (files.length === 0) fail(".github/workflows", 0, "no workflow files");

function block(lines, keyRe) {
  const i = lines.findIndex((l) => keyRe.test(l));
  if (i < 0) return { i, body: [] };
  const body = [];
  for (const l of lines.slice(i + 1)) {
    if (l.trim() !== "" && !/^\s/.test(l)) break;
    body.push(l);
  }
  return { i, body };
}

function triggers(lines) {
  const { i, body } = block(lines, /^(on|"on"|'on'|true):/);
  if (i < 0) return [];
  const inline = lines[i].replace(/^[^:]+:/, "").replace(/#.*$/, "").trim();
  if (inline) return inline.replace(/^\[|\]$/g, "").split(",").map((s) => s.trim()).filter(Boolean);
  return body.map((l) => /^ {2}([A-Za-z_]+):/.exec(l)?.[1]).filter(Boolean);
}

function jobs(lines) {
  const out = new Map();
  const start = lines.findIndex((l) => /^jobs:\s*(#.*)?$/.test(l));
  if (start < 0) return out;
  let cur = null;
  for (let k = start + 1; k < lines.length; k++) {
    const l = lines[k];
    if (/^\S/.test(l) && !/^#/.test(l)) break;
    const m = /^ {2}([A-Za-z0-9_-]+):\s*(#.*)?$/.exec(l);
    if (m) out.set(m[1], (cur = { id: m[1], line: k + 1, body: [] }));
    else if (cur) cur.body.push([k + 1, l]);
  }
  return out;
}

function jobNeeds(job) {
  const idx = job.body.findIndex(([, l]) => /^ {4}needs:/.test(l));
  if (idx < 0) return [];
  const inline = job.body[idx][1].replace(/^ {4}needs:/, "").replace(/#.*$/, "").trim();
  if (inline) return inline.replace(/^\[|\]$/g, "").split(",").map((s) => s.trim()).filter(Boolean);
  const out = [];
  for (const [, l] of job.body.slice(idx + 1)) {
    const m = /^ {6}-\s*([A-Za-z0-9_-]+)/.exec(l);
    if (!m) break;
    out.push(m[1]);
  }
  return out;
}

let aggregators = 0;
for (const f of files) {
  const lines = readFileSync(join(dir, f), "utf8").replace(/\r\n/g, "\n").split("\n");
  const on = triggers(lines);
  const prStarts = on.includes("pull_request") || on.includes("pull_request_target");

  lines.forEach((l, k) => {
    const n = k + 1;
    if (/^\s*#/.test(l)) return;
    const u = /^\s*(?:-\s*)?uses:\s*([^\s#]+)(.*)$/.exec(l);
    if (u && !u[1].startsWith("./")) {
      if (u[1].startsWith("docker://")) {
        if (!/@sha256:[0-9a-f]{64}$/.test(u[1])) fail(f, n, "docker:// action image not pinned by digest");
      } else if (!/@[0-9a-f]{40}$/.test(u[1])) fail(f, n, `action not pinned to a 40-character SHA: ${u[1].split("@")[0]}`);
      else if (!/#\s*\S/.test(u[2])) fail(f, n, "pinned action lacks a '# version' comment");
    }
    const img = /^\s+(?:image|container):\s*["']?([^\s"'#]+)/.exec(l);
    if (img && !/^\$\{\{/.test(img[1]) && !/@sha256:[0-9a-f]{64}$/.test(img[1])) fail(f, n, "container image not pinned by digest");
    if (/continue-on-error:\s*(?!false)\S/.test(l)) {
      const note = `${lines[k - 1] ?? ""} ${l}`;
      const until = /until:\s*(\d{4}-\d{2}-\d{2})/.exec(note);
      if (!/owner:\s*\S+/.test(note) || !until) fail(f, n, 'continue-on-error needs "# owner: <who> until: <YYYY-MM-DD>"');
      else if (until[1] < today) fail(f, n, `continue-on-error expired ${until[1]}: make the check required or delete it`);
    }
    if (/releases\/latest/.test(l)) fail(f, n, "download from releases/latest: pin the release and verify its checksum");
    if (on.includes("pull_request_target") && /^\s*(ref|repository):\s*\$\{\{\s*github\.(event\.pull_request\.head\.|head_ref)/.test(l)) {
      fail(f, n, "pull_request_target with a checkout of the PR head");
    }
  });

  const perms = block(lines, /^permissions:/);
  if (perms.i < 0) fail(f, 1, "no top-level permissions: block (default to contents: read)");
  else if (/write/.test([lines[perms.i], ...perms.body].join("\n"))) fail(f, perms.i + 1, "top-level permissions grant write; widen per job instead");

  const all = jobs(lines);
  for (const job of all.values()) {
    const text = job.body.map(([, l]) => l).filter((l) => !/^\s*#/.test(l)).join("\n");
    const names = [...text.matchAll(/secrets\.([A-Za-z0-9_]+)/g)].map((m) => m[1]).filter((s) => s !== "GITHUB_TOKEN");
    for (const s of new Set(names)) {
      if (!inventory.includes(`\`${s}\``)) fail(f, job.line, `secret ${s} is not listed in docs/security/secret-inventory.md`);
    }
    if (prStarts && names.length) {
      const cond = job.body.find(([, l]) => /^ {4}if:/.test(l))?.[1] ?? "";
      const excludesPr = /event_name\s*(==\s*'(workflow_dispatch|push|schedule|merge_group)'|!=\s*'pull_request')/.test(cond) && !/==\s*'pull_request/.test(cond);
      // A recorded exception: "# exception: secret-on-pr owner: <who> until: <YYYY-MM-DD> — reason"
      const raw = job.body.map(([, l]) => l).join("\n");
      const exc = /#\s*exception:\s*secret-on-pr\s+owner:\s*\S+\s+until:\s*(\d{4}-\d{2}-\d{2})/.exec(raw);
      if (exc && exc[1] < today) fail(f, job.line, `job ${job.id}: secret-on-pr exception expired ${exc[1]}`);
      else if (!excludesPr && !exc) fail(f, job.line, `job ${job.id} reads a stored secret and can run on pull_request`);
    }
  }

  const gate = all.get("ci-green");
  if (gate) {
    aggregators++;
    const text = gate.body.map(([, l]) => l).join("\n");
    if (!/^ {4}if:\s*(\$\{\{\s*)?always\(\)/m.test(text)) fail(f, gate.line, "ci-green must run if: ${{ always() }}");
    if (!/success/.test(text)) fail(f, gate.line, "ci-green must assert every needed result is success");
    const exempt = (/#\s*not gating:\s*([^—\n]+)/.exec(text)?.[1] ?? "").split(",").map((s) => s.trim()).filter(Boolean);
    const needs = new Set(jobNeeds(gate));
    for (const id of all.keys()) {
      if (id !== "ci-green" && !needs.has(id) && !exempt.includes(id)) fail(f, gate.line, `ci-green does not need job ${id}`);
    }
  }
}
if (files.length && aggregators === 0) fail(".github/workflows", 0, "no ci-green aggregator job in any workflow");

if (problems.length) {
  console.error(`workflow doctrine: ${problems.length} problem(s)`);
  for (const p of problems) console.error(`  ${p}`);
  process.exit(1);
}
console.log(`workflow doctrine: ${files.length} workflow file(s), 0 problems`);
