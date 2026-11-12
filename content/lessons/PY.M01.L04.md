---
{
  "id": "PY.M01.L04",
  "title": "Learner workspace in Git + Git placement check",
  "difficulty": "beginner",
  "minutes": 30,
  "prerequisites": ["PY.M01.L03"],
  "objectives": [
    "Set up the exercise workspace: scaffold an exercise, run its tests and import the result",
    "Write a .gitignore that hides generated files and keeps source visible",
    "Know what .gitignore does not do (untrack committed files)",
    "Show your existing Git knowledge in a short placement check (branches, revert, rebase)"
  ],
  "why": "From now on your work lives in workspace/, with one folder per exercise. Keeping it in Git gives you history and a safety net while you learn. Your assessment rated Git as 'not assessed', and this lesson starts working out whether Git needs any time in your curriculum.",
  "applications": [
    "Clean repositories where git status shows only real changes",
    "Undoing a shared mistake safely with revert instead of rewriting history",
    "Knowing when rebasing is safe (local commits) and when it isn't (pushed, shared commits)"
  ],
  "exercises": ["PY.M01.L04.E1"],
  "sources": [
    {
      "title": "gitignore documentation",
      "url": "https://git-scm.com/docs/gitignore",
      "version": "Git docs (latest, 2.55+); behaviour verified locally with git 2.43.0",
      "verified": "2026-11-12",
      "claims": ["gitignore specifies intentionally untracked files; tracked files are not affected", "Stop tracking with git rm --cached", "A trailing slash matches directories only", "A pattern without a leading or middle slash matches at any level"]
    },
    {
      "title": "git-revert documentation",
      "url": "https://git-scm.com/docs/git-revert",
      "version": "Git docs (latest); behaviour verified locally with git 2.43.0",
      "verified": "2026-11-12",
      "claims": ["git revert records new commits that reverse earlier commits", "reset --hard and restore discard uncommitted changes; revert is for undoing commits"]
    },
    {
      "title": "Pro Git, 3.6 Git Branching: Rebasing",
      "url": "https://git-scm.com/book/en/v2/Git-Branching-Rebasing",
      "version": "Pro Git 2nd edition",
      "verified": "2026-11-12",
      "claims": ["Rebasing abandons existing commits and creates new, similar ones", "Don't rebase commits that exist outside your repository that others may have based work on"]
    }
  ]
}
---
## 1. The workspace

You've used this loop since L01. Now you know what each part does: the venv (L02) and pytest (L03).

```console
$ .venv/bin/python tools/scaffold.py PY.M01.L04.E1   # once: copies the starter files
created workspace/PY.M01.L04.E1
$ cd workspace/PY.M01.L04.E1
$ ../../.venv/bin/pytest                           # run the tests (writes result.xml)
```

Then edit, rerun and repeat until it's green, and import `result.xml` on the exercise page as evidence. The scaffold refuses to overwrite an existing folder, so your work is never replaced.

## 2. Git for your work: your decision

You've said "not now" to putting the academy itself under Git, and that stands. **Your own `workspace/` is a separate question.** A repository there gives you `git diff` to see what you changed while fixing a failing test, and lets you commit each solved exercise. If you want it:

```console
$ cd workspace
$ git init
$ cp PY.M01.L04.E1/.gitignore .gitignore     # after you finish the exercise below
$ git add . && git commit -m "Solved PY.M01.L01-L04 exercises"
```

It's optional. Nothing in the academy depends on it.

## 3. .gitignore: what it does and doesn't do

A `.gitignore` lists **untracked files Git should ignore**: things your tools generate, such as `.venv/`, `__pycache__/` and `result.xml`. Without one, `git status` drowns real changes in noise. With one:

```console
$ git status --short
?? .gitignore
?? test_words.py
?? words.py
$ git check-ignore -v PY.M01.L03.E1/result.xml
.gitignore:5:result.xml	PY.M01.L03.E1/result.xml
```

`git check-ignore -v` tells you **which line** matched, which helps when a pattern doesn't behave as you expect.

Pattern rules you need:

- `name/` with a trailing slash matches **directories only**.
- A pattern with **no slash at the start or middle** matches **at any depth**, so `result.xml` also hides `PY.M01.L03.E1/result.xml`.
- `*.pyc` uses glob wildcards.

**What it doesn't do:** ignore a file that's already committed. Git keeps tracking it and keeps showing changes. To stop tracking it, run `git rm --cached FILE`, then add it to `.gitignore`.

```exercise
PY.M01.L04.E1
```

```quiz
{ "id": "q1", "type": "choice",
  "prompt": "The workspace's root .gitignore contains the line `result.xml`. Which result.xml files does Git ignore?",
  "options": ["Only the one next to .gitignore", "result.xml at any depth below the .gitignore", "Only ones that were already committed", "None until .gitignore itself is committed"], "answer": 1,
  "explanation": "No leading or middle slash means it matches at any level. A leading slash, /result.xml, would anchor it to the root only." }
```

## 4. Git placement check

You told me you're comfortable with branches, conflicts, rebasing, code review and history debugging, but your Git history was AI-assisted, so the assessment marked Git **not assessed**. These four questions take about 3 minutes.

**Answer from what you know, with no AI and no docs. Only your first answer counts.**

Four option questions can only show what you *know*, not what you can *do*, so here's what happens next:

- **All four right first time, and E1 passed:** I'll propose taking the Git review out of your curriculum. We confirm it with one short hands-on Git task in a mentor session.
- **Otherwise:** we add a short review aimed at the questions you missed.

Your answers stay in your browser, so the result reaches me only if you tell me, or export your progress from "Your data" and share it. Any curriculum change is then made in `curriculum.json` and `CURRICULUM.md` together, with your approval.

```quiz
{ "id": "q2", "type": "truefalse",
  "prompt": "Adding an already-committed file to .gitignore makes Git stop tracking it.", "answer": false,
  "explanation": "gitignore only affects untracked files. Use git rm --cached FILE to stop tracking, then ignore it." }
```

```quiz
{ "id": "q3", "type": "choice",
  "prompt": "A bad commit is already pushed to the shared main branch and teammates have pulled it. What's the safe way to undo it?",
  "options": ["git revert <commit>, then push", "git reset --hard HEAD~1, then git push --force", "git commit --amend, then push", "Delete main and recreate it"], "answer": 0,
  "explanation": "revert adds a new commit that reverses the bad one, so nobody's history is rewritten. reset plus a force push rewrites shared history." }
```

```quiz
{ "id": "q4", "type": "output",
  "prompt": "In a repository on main you run `git switch -c feature`. What does the next command print?",
  "code": "# git rev-parse --abbrev-ref HEAD",
  "answer": "feature",
  "explanation": "switch -c creates the branch and moves HEAD to it. rev-parse --abbrev-ref HEAD prints the current branch name." }
```

```quiz
{ "id": "q5", "type": "choice",
  "prompt": "Which statement about `git rebase` is true?",
  "options": ["It replays your commits as new commits with new hashes", "It never changes existing history", "It's safe on commits that teammates have already pulled", "It's the same as merge, just faster"], "answer": 0,
  "explanation": "Rebasing abandons the old commits and creates new ones. It's fine on local, unpushed work and harmful on shared commits others have built on." }
```

## 5. Module wrap-up

You can now run Python four ways, keep projects isolated, read pytest failures, and keep a clean workspace. The **module assessment PY.M01.A** checks all four, a few days later if you can manage it, without the lessons open.
