# GitHub setup (Ashwin, once)

1. Create an empty repository on GitHub. A public repository is recommended for this non-commercial project; branch protection on private repositories needs a paid plan.
2. Unzip the project, open a terminal in the `weathergpt` folder and run:
   - `git init -b main`
   - `git add .`
   - `git commit -m "Initial project pack"`
   - `git remote add origin https://github.com/ashwinyadav09/WeatherGPT.git`
   - `git push -u origin main`
3. Fill the `github` column in `team/members.csv` with each person's GitHub username and commit it.
4. Install the GitHub CLI and run `gh auth login`.
5. Preview, then run the bootstrap (labels, milestones, issues with owners and blocking links, CODEOWNERS, branch protection, collaborator invites):
   - `python scripts/github/bootstrap.py --dry-run`
   - `python scripts/github/bootstrap.py --protect --invite`
   The script is safe to re-run; it skips what already exists and writes `team/issue-map.json`.
6. Aman and Pradeep accept the invitation, then each:
   - clones the repository, installs Docker, Python 3.12, Node.js 20+ and ffmpeg
   - copies `.env.example` to `.env` and fills in their keys
   - runs `python scripts/dev.py doctor` and fixes anything it reports
   - opens the folder in Antigravity and pastes their kickoff prompt from `team/prompts/<name>.md`
7. Optional later: add Actions secrets for the weekly contract check (`gh secret set IMD_API_KEY`, and so on) once the IMD key arrives.

If branch protection or invites fail (plan limits or missing permissions), the script prints what to click in Settings. The team workflow still works by convention: nobody pushes to `main`.
