# Crucible CLI Autocomplete

The `crucible` command-line tool supports intelligent shell autocomplete for commands, subcommands, options, and file paths.

## Quick Start

Install autocomplete with a single command:

```bash
# Auto-detects your shell (bash, zsh, fish, or tcsh)
crucible completion

# Or specify explicitly
crucible completion bash
crucible completion zsh
```

Then activate it:

```bash
# For bash
source ~/.bashrc

# For zsh
source ~/.zshrc

# For fish - just restart your terminal
```

## What Gets Autocompleted

Once installed, you get intelligent completions:

### Commands and Subcommands
```bash
crucible <TAB>              # Shows: upload, completion
crucible upload <TAB>       # Shows all upload options
```

### Dataset Types
```bash
crucible upload -i file.lmp -t <TAB>
# Shows: LAMMPS, lammps, md
```

### File Paths
```bash
crucible upload -i <TAB>
# Completes file paths intelligently
# (shows .lmp files in current directory)
```

### Options
```bash
crucible upload -<TAB>
# Shows: -i, -t, -pid, -u, --mfid, -n, --orcid, -v, etc.
```

## Manual Installation

If you prefer manual setup, add this to your shell config:

### Bash (~/.bashrc)
```bash
eval "$(register-python-argcomplete crucible)"
```

### Zsh (~/.zshrc)
```bash
autoload -U bashcompinit
bashcompinit
eval "$(register-python-argcomplete crucible)"
```

### Fish (~/.config/fish/completions/crucible.fish)
```bash
register-python-argcomplete --shell fish crucible | source
```

### Tcsh (~/.tcshrc)
```bash
eval `register-python-argcomplete --shell tcsh crucible`
```

## Viewing Completion Scripts

To see what will be installed without actually installing:

```bash
crucible completion bash --print
crucible completion zsh --print
```

## Uninstalling

To remove autocomplete, simply delete the relevant lines from your shell config file:

```bash
# For bash
vim ~/.bashrc
# Remove the line: eval "$(register-python-argcomplete crucible)"

# For zsh
vim ~/.zshrc
# Remove the argcomplete lines

# For fish
rm ~/.config/fish/completions/crucible.fish
```

## Troubleshooting

### Completion not working after installation

1. Make sure argcomplete is installed:
   ```bash
   pip install argcomplete
   ```

2. Activate your shell config:
   ```bash
   source ~/.bashrc  # or ~/.zshrc
   ```

3. Try in a new terminal window

### "register-python-argcomplete: command not found"

This means argcomplete isn't installed or isn't in your PATH:

```bash
pip install argcomplete
```

### Completion shows raw options instead of intelligent suggestions

Make sure you've sourced your config file after installation:

```bash
source ~/.bashrc  # or appropriate config file
```

## How It Works

The autocomplete system uses Python's `argcomplete` library, which:

1. Hooks into your shell's completion system
2. Parses the `crucible` CLI's argument structure
3. Provides context-aware completions based on:
   - Available subcommands
   - Registered parser types
   - File system for path arguments
   - Defined choices for constrained options

## For Developers

When adding new subcommands or parsers, autocomplete works automatically!

### Adding Custom Completers

You can add custom completers to specific arguments:

```python
from argcomplete.completers import FilesCompleter

# In your subcommand registration:
arg = parser.add_argument('-i', '--input')
arg.completer = FilesCompleter(allowednames=('.lmp', '.dat'))  # Only .lmp and .dat files

# Or custom function:
def project_completer(**kwargs):
    # Could query Crucible API for project list
    return ['10k_perovskites', 'lammps-test', 'my-project']

arg = parser.add_argument('-pid', '--project-id')
arg.completer = project_completer
```

This is already set up for:
- Input files (FilesCompleter)
- Dataset types (shows parser registry keys)
