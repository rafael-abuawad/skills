# Using this folder on another computer

After you clone or sync the repo so `skills/` exists locally, point Cursor and other agents at this directory (adjust the path if your checkout lives elsewhere):

```bash
CANONICAL="/absolute/path/to/dev-container/skills"

# backup existing trees if they are real directories
[ -d ~/.cursor/skills ] && [ ! -L ~/.cursor/skills ] && mv ~/.cursor/skills ~/.cursor/skills.pre-shared-backup
[ -d ~/.agents/skills ] && [ ! -L ~/.agents/skills ] && mv ~/.agents/skills ~/.agents/skills.pre-shared-backup

ln -sfn "$CANONICAL" ~/.cursor/skills
ln -sfn "$CANONICAL" ~/.agents/skills
```

Restart Cursor if skills do not show up immediately.

## Skill families

`web3-react/SKILL.md` and `fyzz/SKILL.md` remain the entry points. Their companion
skills live in `web3-react/skills/<skill-name>/` and `fyzz/skills/<skill-name>/`.
Invocation names are unchanged; each companion retains its own `SKILL.md` and
supporting files. Entry-point links resolve directly to the nested skills.

Check the installed agent's skill list after syncing: it should include nine
Web3 React skills and three Fyzz skills. Recursive discovery is required to list
all companions independently. If a client scans only direct children of its
configured skill roots, also configure `web3-react/skills/` and `fyzz/skills/` as
roots using that client's supported settings. The repository does not create
compatibility aliases or modify client configuration.
