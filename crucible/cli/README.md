# CLI contributor notes

The published CLI documentation is canonical:

- [CLI overview](../../docs/cli/index.md)
- [Command reference](../../docs/cli/reference.md)

Do not maintain a second command inventory in this directory. When adding or changing a command, update its argparse help and the published command reference in the same change.

For implementation conventions, see:

- [Display guide](DISPLAY_GUIDE.md)
- [Known CLI inconsistencies](KNOWN_ISSUES.md)
- [CLI development skill](../../skills/nano-crucible-cli-development/SKILL.md)
