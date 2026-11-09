# Configuration Management (Config)

`Config` is a singleton YAML-based configuration system with environment layering, deep merging, token substitution, and automatic backup.

Recall that you must first initialize the package with `neutrons_standard.init()` before using `Config`. See the [Quick Start](README.md#quick-start) section for details.

## Configuration File Structure

Configuration files are YAML format and can be organized in a hierarchical structure.
The base configuration file is `application.yml`, and environment-specific configurations are named according to the environment (e.g., `production.yml`, `qa.yml`).
See [Configuration Layering](#configuration-layering) for details on how these files are merged.

## Quick Reference

```python
from neutrons_standard import Config

# Access values
Config["database.host"]  # Dot-delimited lookup
Config.exists("optional.key")  # Check if key exists

# Environment management
Config.load_env("production.yml")  # Load environment config
Config.reload(env_name="qa.yml")  # Reload with environment
Config.get_current_env()  # Get current environment name

# User config
Config.swap_to_user_yml()  # Use ~/.config/{package_name}/{package_name}-user.yml
Config.should_swap_to_user_yml()  # Check if user config available

# Backup
Config.persist_backup()  # Backup to ~/.config/{package_name}/application.yml.bak
Config.archive_user_yml()  # Archive versioned user config
```

### Dot-Delimited Lookup

Access nested values with dot notation. Automatically resolves token substitutions:

```python
Config["database.host"]  # localhost
Config["paths.input"]  # /data/input (resolved from ${paths.base}/input)
Config.exists("optional.setting")  # Returns bool
```

### Environment Configuration

Specify environment via:

- Environment variable: `env=environment_name`
- YAML property: `environment: environment_name`
- Auto-detect user config: `~/.config/{package_name}/{package_name}-user.yml`

### Configuration Layering

When an environment is specified (as above), the base configuration (`application.yml`) and environment overrides (e.g., `production.yml`) are merged recursively, for example:

**Base (application.yml):**

```yaml
database:
  host: localhost
  port: 5432
  credentials:
    username: user
    password: pass
```

**Override (production.yml):**

```yaml
database:
  host: prod-db.example.com
  credentials:
    password: secure-pass
```

**Result (merged):**

```yaml
database:
  host: prod-db.example.com # Overridden
  port: 5432 # From base (preserved)
  credentials:
    username: user # From base (preserved)
    password: secure-pass # Overridden
```

**Merge rules:**

- Dictionaries merge recursively
- Scalar values replace entirely
- New keys added
- Nothing deleted

### Token Substitution

Reference other config values with `${key.subkey}` syntax:

```yaml
paths:
  base: /data
  input: ${paths.base}/input # Resolves to /data/input
  output: ${paths.base}/output

module:
  root: /app # Auto-set by Config
```

### User Configuration Management

User config (`~/.config/{package_name}/{package_name}-user.yml`) auto-loads if present, no explicit `env` is specified, and this is not a test run. If its `application.version` does not match the installed version, it is archived and regenerated from `application.yml`, replacing any hand edits. Only the newest `application.user_yml_archive_limit` archives are kept: 5 by default, `-1` keeps all of them (unlimited), and `0` keeps none. Set it in `application.yml` or an environment file:

```yaml
application:
  user_yml_archive_limit: 5 # -1: unlimited, 0: keep none
```

Any other value logs a warning, and the default is used.

Older releases kept these files in `~/.{package_name}/`. If `~/.config/{package_name}/` doesn't exist yet,
`~/.{package_name}/` is moved there the first time it is needed, and a warning is logged.

### Configuration Backup

Backups are created automatically: `application.yml.bak` (the full merged config) on every `Config.reload()`, and a versioned `-user` archive before an out-of-date user config is regenerated (newest `application.user_yml_archive_limit` kept):

```text
~/.config/{package_name}/
├── application.yml.bak                          # Latest backup
└── {package_name}-user-1.0.0-2026-03-04T16:10:34.817Z.yml.bak  # Versioned
```

### Deployment Configuration

Auto-select environment based on app version:

```python
Config.configure_for_deploy()
```

- Contains `dev` → NEXT environment (`{package_name}_next`)
- Contains `rc` → QA environment (`{package_name}_qa`)
- Otherwise → PROD environment (`{package_name}_prod`)

Merges and exports to `application.yml`.

The deployments are the members of `DeployEnvEnum`, whose values are `next`, `qa` and `prod`. Use
`env_name()` for the client's environment name:

```python
from neutrons_standard.config import DeployEnvEnum

DeployEnvEnum.NEXT  # "next"
DeployEnvEnum.NEXT.env_name()  # "{package_name}_next"
Config.load_env(DeployEnvEnum.QA.env_name())
```

Before this release the values were the environment names themselves (`DeployEnvEnum.NEXT == "{package_name}_next"`):
code that passes a member as an environment name, such as `Config.load_env(DeployEnvEnum.QA)`, must call
`env_name()`.

### Directory Path Expansion

Any string value that is `~` or starts with `~/` is expanded to the user's home directory when it is read,
including values produced by `${...}` substitution. The stored config (and files written from it) keep the `~`.

```yaml
data:
  home: ~/data # Config["data.home"] == "/home/user/data"
output:
  dir: ${data.home}/output # Config["output.dir"] == "/home/user/data/output"
```

`~user` expands to that user's home directory. If the user doesn't exist, a warning is logged once and the value is
used as written. A `~` anywhere other than the start of the value is left unchanged.

### Error Handling

Failed config loading automatically restores previous state:

```python
try:
    Config.load_env("invalid.yml")  # Fails, restores previous
except Exception:
    pass  # Config unchanged

try:
    value = Config["nonexistent"]  # Raises KeyError
except KeyError:
    pass
```

## Examples

### Basic Usage

```python
from neutrons_standard import Config

# Read values
host = Config["database.host"]

# Safe access with check
if Config.exists("optional.feature"):
    feature_dir = Config["optional.feature"]

# Switch environment
Config.load_env("production.yml")
prod_host = Config["database.host"]
```

### Configuration File Example

```yaml
application:
  version: 1.0.0

environment: default

database:
  host: localhost
  port: 5432
  credentials:
    username: app_user
    password: app_pass

paths:
  base: /data
  input: ${paths.base}/input
  output: ${paths.base}/output
  resources: ${module.root}/resources

logging:
  level: INFO
  file: app.log

# Set automatically
module:
  root: /app
```
