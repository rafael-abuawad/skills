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