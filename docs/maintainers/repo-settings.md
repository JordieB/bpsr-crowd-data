# Repository Settings & Rules

## General → Features

- [x] Issues — **On**

- [x] Discussions — **On**

- [ ] Wikis — **Off** (Docs live in `/docs`; changes reviewed via PR)

- [ ] Template repository — Off (not a template)

- [ ] Sponsorships — Optional

- [ ] Projects — Optional

## General → Pull Requests

- [ ] Allow merge commits — **Off**

- [x] Allow squash merging — **On** (single-commit PRs; clean history)

- [ ] Allow rebase merging — **Off**

- [x] Always suggest updating PR branches — **On**

- [ ] Allow auto-merge — **Off** (enable later when trust & CI mature)

- [x] Automatically delete head branches — **On**

## General → Pushes / Archives

- [ ] Limit branches/tags per push — Off (enable only if abuse appears)

- [ ] Include Git LFS objects in archives — Only if using LFS

- Default branch: `main`

## Ruleset (Settings → Rules)

- Target: `Default` (covers `main`)

- Branch protections:

  - [x] Restrict deletions — **On**

  - [x] Require a pull request before merging — **On**

    - Required approvals: **1**

    - [x] Dismiss stale approvals on new commits

    - [x] Require approval of the most recent reviewable push

    - [x] Require conversation resolution

    - [x] Require review from CODEOWNERS (once `CODEOWNERS` exists)

  - Merge methods: **Squash only**

  - [x] Require status checks to pass — **On**

  - [x] Require branches to be up to date — **On**

  - [x] Block force pushes — **On**

  - [ ] Require linear history — Off (squash already keeps history clean)

  - [ ] Require deployments to succeed — Off (enable when envs exist)

  - [ ] Require signed commits — Off for newcomers (revisit later)

## Post-CI reminder

After the `CI` workflow exposes checks named **`build`**, **`lint`**, **`test`** on PRs:

1. Settings → Rules → <ruleset> → **Require status checks to pass** → **Add checks**: `build`, `lint`, `test`

2. Turn **off** "Do not require status checks on creation"

3. Keep **Require branches to be up to date** enabled

## Rationale

- Squash-only + required reviews = minimal, auditable history.

- Discussions reduces issue noise from support/Q&A.

- No wiki to prevent unreviewed drift; docs via PRs.

- Auto-merge disabled until the team and CI are stable.

