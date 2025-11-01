# Project Management

## Enforce required status checks (post-CI)

After the `CI` workflow is merged and visible on PRs, go to:

Settings → Rules → <your ruleset>:

- Turn **on** "Require status checks to pass".

- Click **Add checks** and add: `build`, `lint`, `test`.

- Turn **on** "Require branches to be up to date before merging".

- **Turn off** "Do not require status checks on creation".

- Keep merge method as **Squash** only.

## CODEOWNERS

The CODEOWNERS file is located at `.github/CODEOWNERS`. This file defines default code owners for all files in the repository.

To add path-specific owners, uncomment and modify the path-specific entries in the CODEOWNERS file, for example:

```
/docs/ @JordieB
/scripts/ @JordieB
```

