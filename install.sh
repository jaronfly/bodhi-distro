#!/usr/bin/env bash
# Bodhi seed installer for macOS, Linux and WSL.
#
#   ./install.sh                      from a clone of this repository
#   curl -fsSL <raw url>/install.sh | bash     (works once the repository is public)
#
# What it does, asking before each step that installs or changes anything:
#   1. looks at this computer and says what is there, in plain words;
#   2. gets the seed (uses this clone, or clones to ~/.bodhi/seed);
#   3. asks the setup questions (bin/bodhi.py setup);
#   4. adds the Bodhi skill to the AI tools you use (Claude Code, Codex, OpenClaw, Hermes);
#   5. offers the optional Bodhi skills, one at a time, each off unless you say yes;
#   6. offers optional tools (Ollama, Obsidian) and links to others;
#   7. offers to create your Bodhi folder (the vault);
#   8. runs bin/bodhi.py doctor and prints the first message to paste.
#
# Options:
#   --yes                   unattended: safe defaults only (see below)
#   --dry-run               print the plan; change nothing, write nothing
#   --plain                 no color (NO_COLOR is honoured too)
#   --update                pull the latest seed and refresh every skill copy it made
#   --uninstall             remove what the install record lists, and nothing else
#   --dir PATH              where to clone the seed (default ~/.bodhi/seed)
#   --vault PATH            create the vault here (with --yes, only when given)
#   --answers PATH          use saved setup answers instead of asking
#   --install LIST          with --yes: tools you allow it to install, comma-separated:
#                           claude-code, codex, hermes, ollama, obsidian, prerequisites (git, python3)
#   --skills LIST           with --yes: optional Bodhi skills to add, comma-separated
#                           (bodhi-orchestrator, bodhi-grill, bodhi-nap, bodhi-synthesis); default none
#   --allow-sudo            with --yes: allow steps that need sudo
#   --allow-remote-scripts  with --yes: allow running an installer script downloaded from the internet
#
# With --yes it never uses sudo and never runs a downloaded installer unless the two
# --allow flags say so, installs no software you did not name in --install, and adds no
# optional skill you did not name in --skills. A short sprout animation plays at the end on
# a terminal with color; --plain, NO_COLOR, CI or BODHI_NO_MOTION=1 skip it.
# It never stores API keys: each AI tool signs you in itself. It sends nothing anywhere.
# Record of what it did: ~/.bodhi/install-manifest.json. Log: ~/.bodhi/install.log.
#
# Written for bash 3.2 (the macOS default): no associative arrays, no ${x,,}.
set -u

BODHI_REPO_URL="${BODHI_REPO_URL:-https://github.com/jaronfly/bodhi-distro.git}"
BODHI_HOME="${BODHI_HOME:-$HOME/.bodhi}"
LOG_FILE="$BODHI_HOME/install.log"
ANSWERS_FILE="$BODHI_HOME/answers.json"

MODE=install
YES=false
DRY_RUN=false
PLAIN=false
ALLOW_SUDO=false
ALLOW_REMOTE=false
WANT_INSTALL=""
WANT_SKILLS=""
SEED_TARGETS=""
VAULT_PATH=""
SEED_DIR=""
ANSWERS_ARG=""
NO_MORE_INPUT=false
CHANGES=0

usage() { sed -n '2,/^set -u$/p' "$0" 2>/dev/null | sed '$d' | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
    case "$1" in
        --yes|-y) YES=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --plain) PLAIN=true; shift ;;
        --update) MODE=update; shift ;;
        --uninstall) MODE=uninstall; shift ;;
        --allow-sudo) ALLOW_SUDO=true; shift ;;
        --allow-remote-scripts) ALLOW_REMOTE=true; shift ;;
        --dir|--vault|--answers|--install|--skills)
            if [ $# -lt 2 ] || [ -z "$2" ]; then echo "install.sh: $1 needs a value" >&2; exit 2; fi
            case "$1" in
                --dir) SEED_DIR="$2" ;;
                --vault) VAULT_PATH="$2" ;;
                --answers) ANSWERS_ARG="$2" ;;
                --install) WANT_INSTALL=",$2," ;;
                --skills) WANT_SKILLS=",$2," ;;
            esac
            shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "install.sh: unknown option $1 (try --help)" >&2; exit 2 ;;
    esac
done

PLAIN_FLAG=""
if [ "$PLAIN" = true ] || [ -n "${NO_COLOR:-}" ]; then PLAIN_FLAG=yes; fi

# ---------------------------------------------------------------- output ----
# Words carry every meaning; color only decorates, and only on a terminal.
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ] && [ "$PLAIN" = false ] && [ "${TERM:-}" != dumb ]; then
    C_BOLD=$'\033[1m' C_DIM=$'\033[2m' C_GREEN=$'\033[32m' C_YELLOW=$'\033[33m' C_OFF=$'\033[0m'
else
    C_BOLD="" C_DIM="" C_GREEN="" C_YELLOW="" C_OFF=""
fi

log() {
    if [ "$DRY_RUN" = false ] && [ -d "$BODHI_HOME" ]; then
        printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$LOG_FILE"
    fi
}
say() { printf '%s\n' "$*"; log "$*"; }
heading() { printf '\n%s%s%s\n' "$C_BOLD" "$*" "$C_OFF"; log "== $*"; }
ok() { printf '  %sok%s    %s\n' "$C_GREEN" "$C_OFF" "$*"; log "ok $*"; }
note() { printf '  note  %s\n' "$*"; log "note $*"; }
warn() { printf '  %swarn%s  %s\n' "$C_YELLOW" "$C_OFF" "$*"; log "warn $*"; }
detail() { printf '        %s%s%s\n' "$C_DIM" "$*" "$C_OFF"; }
die() { printf 'install.sh: %s\n' "$*" >&2; log "stopped: $*"; exit 1; }

# ----------------------------------------------------------------- input ----
# Run from a file, answers come on stdin. Under `curl | bash`, stdin is the script
# itself, so answers come from the terminal (/dev/tty), as Hermes's installer does.
INPUT_FD=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    exec 3<&0
    INPUT_FD=3
else
    SCRIPT_DIR=""
    if (: </dev/tty) 2>/dev/null; then
        exec 3</dev/tty
        INPUT_FD=3
    fi
fi
if [ -z "$INPUT_FD" ] && [ "$YES" = false ]; then
    YES=true
    NO_TERMINAL=true
else
    NO_TERMINAL=false
fi

input_is_terminal() { [ -n "$INPUT_FD" ] && [ -t 3 ]; }

in_list() { case "$WANT_INSTALL" in *",$1,"*) return 0 ;; esac; return 1; }
in_skills() { case "$WANT_SKILLS" in *",$1,"*) return 0 ;; esac; return 1; }

# confirm LEVEL DEFAULT QUESTION
#   LEVEL safe    a reversible change the installer records (a skill copy, the vault)
#         optin   an optional extra, off by default (an optional Bodhi skill)
#         install installs software with a package manager
#         sudo    needs administrator rights
#         remote  runs an installer script downloaded from the internet
#   DEFAULT y or n. Returns 0 for yes.
CONFIRM_TOOL=""
confirm() {
    local level="$1" default="$2" question="$3" answer hint
    if [ "$DRY_RUN" = true ]; then
        detail "would ask: $question"
        return 0
    fi
    if [ "$YES" = true ]; then
        case "$level" in
            safe) return 0 ;;
            optin) in_skills "$CONFIRM_TOOL" && return 0 ;;
            install) in_list "$CONFIRM_TOOL" && return 0 ;;
            sudo) [ "$ALLOW_SUDO" = true ] && in_list "$CONFIRM_TOOL" && return 0 ;;
            remote) [ "$ALLOW_REMOTE" = true ] && in_list "$CONFIRM_TOOL" && return 0 ;;
        esac
        case "$level" in
            optin) note "skipped: $question (unattended; name it in --skills to add it)" ;;
            install) note "skipped: $question (unattended; name it in --install to allow)" ;;
            sudo) note "skipped: $question (unattended; needs --install and --allow-sudo)" ;;
            remote) note "skipped: $question (unattended; needs --install and --allow-remote-scripts)" ;;
        esac
        return 1
    fi
    if [ "$NO_MORE_INPUT" = true ]; then
        return 1
    fi
    if [ "$default" = y ]; then hint="[Y/n]"; else hint="[y/N]"; fi
    printf '%s %s ' "$question" "$hint"
    if ! IFS= read -r -u "$INPUT_FD" answer; then
        printf '\n'
        note "no more answers came in, so everything from here is a no"
        NO_MORE_INPUT=true
        log "answer: <end of input> -> no"
        return 1
    fi
    input_is_terminal || printf '%s\n' "$answer"
    log "answer to '$question': ${answer:-<enter>}"
    case "$answer" in
        "") [ "$default" = y ] ;;
        y|Y|yes|Yes|YES) return 0 ;;
        *) return 1 ;;
    esac
}

# run DESCRIPTION -- COMMAND...   (logged; printed instead of run under --dry-run)
run() {
    local description="$1"
    shift
    [ "$1" = "--" ] && shift
    if [ "$DRY_RUN" = true ]; then
        detail "would run: $*"
        return 0
    fi
    log "run: $*"
    if "$@" >> "$LOG_FILE" 2>&1; then
        log "done: $description"
        return 0
    fi
    warn "$description failed; see $LOG_FILE"
    return 1
}

# run_shell DESCRIPTION COMMAND_STRING   (for pipes such as curl | bash; shown exactly)
run_shell() {
    local description="$1" command="$2"
    if [ "$DRY_RUN" = true ]; then
        detail "would run: $command"
        return 0
    fi
    log "run: $command"
    # Interactive installers (Hermes's wizard, Homebrew's prompt) need the terminal.
    if input_is_terminal; then
        bash -c "$command" <&3
    else
        bash -c "$command" </dev/null >> "$LOG_FILE" 2>&1
    fi
    local status=$?
    if [ "$status" -eq 0 ]; then
        log "done: $description"
    else
        warn "$description failed (exit $status); see $LOG_FILE"
    fi
    return "$status"
}

have() { command -v "$1" >/dev/null 2>&1; }
helper() { python3 "$SEED_DIR/bin/bodhi_install.py" "$@"; }

# ------------------------------------------------------------ preflight ----
OS_NAME="" ARCH="" PKG="" PY_OK=false IS_WSL=false
preflight() {
    heading "Looking at this computer (nothing is changed here)"
    case "$(uname -s 2>/dev/null)" in
        Darwin) OS_NAME=macos ;;
        Linux) OS_NAME=linux
               if grep -qi microsoft /proc/version 2>/dev/null; then IS_WSL=true; fi ;;
        *) die "this installer supports macOS, Linux and WSL. On Windows, install WSL first (see docs/INSTALL.md), or copy the skill by hand." ;;
    esac
    ARCH="$(uname -m 2>/dev/null)"
    if [ "$IS_WSL" = true ]; then ok "Linux on Windows (WSL), $ARCH"; else ok "$OS_NAME, $ARCH"; fi
    for candidate in brew apt-get dnf pacman; do
        if have "$candidate"; then PKG="$candidate"; break; fi
    done
    if [ -n "$PKG" ]; then ok "package manager: $PKG"; else note "no package manager found (Homebrew, apt, dnf or pacman)"; fi
    if have git; then ok "git: $(git --version 2>/dev/null | head -n 1)"; else warn "git is not installed; the seed and the vault need it"; fi
    if have python3; then
        local version
        version="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)"
        if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
            PY_OK=true
            ok "python3 $version"
        else
            warn "python3 $version is older than 3.9, which Bodhi needs"
        fi
    else
        warn "python3 is not installed; Bodhi needs version 3.9 or newer"
    fi
    if have node; then ok "node $(node --version 2>/dev/null) (only some AI tools need it)"; fi
    FOUND_HARNESSES=""
    local label command
    for pair in "claude:Claude Code" "codex:Codex" "hermes:Hermes Agent" "openclaw:OpenClaw"; do
        command="${pair%%:*}"; label="${pair#*:}"
        if have "$command"; then ok "$label is installed"; FOUND_HARNESSES="$FOUND_HARNESSES $command"; fi
    done
    [ -n "$FOUND_HARNESSES" ] || note "no AI app that reads skills was found (Claude Code, Codex, Hermes, OpenClaw)"
    if have ollama; then ok "Ollama is installed (local models)"; fi
    if have lms || [ -d "/Applications/LM Studio.app" ]; then ok "LM Studio is installed (local models)"; fi
    if have obsidian || [ -d "/Applications/Obsidian.app" ] || [ -d "$HOME/.config/obsidian" ]; then ok "Obsidian is installed (notes)"; fi
}

install_prerequisites() {
    local need=""
    have git || need="$need git"
    [ "$PY_OK" = true ] || need="$need python3"
    [ -n "$need" ] || return 0
    heading "Missing:$need"
    local command="" level=install
    case "$PKG" in
        brew) command="brew install"
              case "$need" in *git*) command="$command git" ;; esac
              case "$need" in *python3*) command="$command python@3.13" ;; esac ;;
        apt-get) command="sudo apt-get install -y$need"; level=sudo ;;
        dnf) command="sudo dnf install -y$need"; level=sudo ;;
        pacman) command="sudo pacman -S --needed${need//python3/python}"; level=sudo ;;
    esac
    if [ -z "$command" ]; then
        die "please install$need yourself (python.org has Python; git-scm.com has Git), then run this again."
    fi
    say "  What: the tools Bodhi runs on:$need."
    say "  Why: the seed is a Git repository, and its tools are Python scripts."
    say "  Command: $command"
    [ "$level" = sudo ] && say "  This needs administrator rights (sudo), because $PKG installs system packages. Your password goes to sudo, never to this script."
    CONFIRM_TOOL=prerequisites
    if confirm "$level" n "Install$need now?"; then
        run_shell "install$need" "$command" || die "could not install$need; install it yourself and run this again."
        CHANGES=$((CHANGES + 1))
        [ "$DRY_RUN" = true ] && return 0
        if ! have git || ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
            die "git and python3 3.9+ are still not both available; open a new terminal and run this again."
        fi
        PY_OK=true
    else
        die "Bodhi needs$need. Install it, then run this again."
    fi
}

# ----------------------------------------------------------------- seed ----
get_seed() {
    heading "The seed"
    if [ -z "$SEED_DIR" ] && [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/bin/bodhi.py" ] && [ -d "$SCRIPT_DIR/skills/bodhi-seed" ]; then
        SEED_DIR="$SCRIPT_DIR"
        ok "using the seed in this folder: $SEED_DIR"
        SEED_KIND="seed-in-place"
        return 0
    fi
    SEED_DIR="${SEED_DIR:-$BODHI_HOME/seed}"
    SEED_KIND=clone
    if [ -d "$SEED_DIR/.git" ]; then
        ok "the seed is already at $SEED_DIR"
        return 0
    fi
    say "  What: a copy of the Bodhi seed repository (text files and small Python scripts)."
    say "  Where: $SEED_DIR"
    say "  Command: git clone --depth 1 $BODHI_REPO_URL $SEED_DIR"
    if confirm safe y "Download the seed there?"; then
        if [ "$DRY_RUN" = true ]; then detail "would run: git clone --depth 1 $BODHI_REPO_URL $SEED_DIR"; return 0; fi
        mkdir -p "$(dirname "$SEED_DIR")"
        if ! GIT_TERMINAL_PROMPT=0 git clone --quiet --depth 1 "$BODHI_REPO_URL" "$SEED_DIR" >> "$LOG_FILE" 2>&1; then
            die "could not clone $BODHI_REPO_URL. While the repository is private this needs your GitHub access: clone it yourself, then run ./install.sh inside the clone."
        fi
        ok "seed downloaded"
        CHANGES=$((CHANGES + 1))
    else
        die "nothing to install without the seed."
    fi
}

record_seed() {
    [ "$DRY_RUN" = true ] && return 0
    helper set-seed --path "$SEED_DIR" --kind "$SEED_KIND" >/dev/null
}

# ------------------------------------------------------------ questions ----
answers_value() {
    # answers_value KEY -> the saved answer, or empty
    [ -f "$ANSWERS_FILE" ] || return 0
    python3 -c 'import json,sys; v=json.load(open(sys.argv[1])).get(sys.argv[2], ""); print(v if isinstance(v, str) else ",".join(v))' "$ANSWERS_FILE" "$1" 2>/dev/null
}

setup_questions() {
    heading "Setup questions"
    if [ -n "$ANSWERS_ARG" ]; then
        say "  Using the answers in $ANSWERS_ARG."
        if [ "$DRY_RUN" = false ]; then
            python3 "$SEED_DIR/bin/bodhi.py" setup --answers "$ANSWERS_ARG" --save "$ANSWERS_FILE" >> "$LOG_FILE" 2>&1 || die "those answers are not valid; see $LOG_FILE"
        fi
    elif [ -f "$ANSWERS_FILE" ]; then
        ok "your saved answers are in $ANSWERS_FILE"
        if input_is_terminal && [ "$YES" = false ] && confirm safe n "Answer the questions again?"; then
            python3 "$SEED_DIR/bin/bodhi.py" setup --save "$ANSWERS_FILE" ${PLAIN_FLAG:+--plain} <&3 || die "setup stopped"
        fi
    elif [ "$DRY_RUN" = true ]; then
        detail "would ask the setup questions (python3 bin/bodhi.py setup) and save them to $ANSWERS_FILE"
        return 0
    elif input_is_terminal && [ "$YES" = false ]; then
        python3 "$SEED_DIR/bin/bodhi.py" setup --save "$ANSWERS_FILE" ${PLAIN_FLAG:+--plain} <&3 || die "setup stopped; nothing else was changed"
    else
        # From a pipe the questions cannot be asked safely, so save what was detected.
        note "no terminal for questions: saving detected defaults (answer later with: python3 bin/bodhi.py setup)"
        python3 "$SEED_DIR/bin/bodhi.py" setup --yes --save "$ANSWERS_FILE" >> "$LOG_FILE" 2>&1 || die "could not save default answers"
    fi
    [ "$DRY_RUN" = false ] && helper record --kind file --path "$ANSWERS_FILE" --label "setup answers" >/dev/null
    return 0
}

# ------------------------------------------------------------- harnesses ----
harness_install_command() {
    # Prints LEVEL, COMMAND and URL separated by tabs (commands may contain a pipe) for one AI tool, preferring a package manager.
    # Commands checked against each tool's own docs on 2026-09-30 (see docs/ONBOARDING_UX.md).
    case "$1" in
        claude-code)
            if [ "$OS_NAME" = macos ] && [ "$PKG" = brew ]; then printf '%s\t%s\t%s\n' "install" "brew install --cask claude-code" ""
            elif have npm && [ "$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)" -ge 22 ]; then printf '%s\t%s\t%s\n' "install" "npm install -g @anthropic-ai/claude-code" ""
            else printf '%s\t%s\t%s\n' "remote" "curl -fsSL https://claude.ai/install.sh | bash" "https://claude.ai/install.sh"; fi ;;
        codex)
            if [ "$OS_NAME" = macos ] && [ "$PKG" = brew ]; then printf '%s\t%s\t%s\n' "install" "brew install --cask codex" ""
            elif have npm; then printf '%s\t%s\t%s\n' "install" "npm install -g @openai/codex" ""
            else printf '%s\t%s\t%s\n' "remote" "curl -fsSL https://chatgpt.com/codex/install.sh | sh" "https://chatgpt.com/codex/install.sh"; fi ;;
        hermes)
            printf '%s\t%s\t%s\n' "remote" "curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash" "https://hermes-agent.nousresearch.com/install.sh" ;;
        ollama)
            if [ "$PKG" = brew ]; then printf '%s\t%s\t%s\n' "install" "brew install ollama" ""
            elif [ "$OS_NAME" = linux ]; then printf '%s\t%s\t%s\n' "remote" "curl -fsSL https://ollama.com/install.sh | sh" "https://ollama.com/install.sh"
            else printf '%s\t%s\t%s\n' "link" "" "https://ollama.com/download"; fi ;;
        obsidian)
            if [ "$OS_NAME" = macos ] && [ "$PKG" = brew ]; then printf '%s\t%s\t%s\n' "install" "brew install --cask obsidian" ""
            else printf '%s\t%s\t%s\n' "link" "" "https://obsidian.md/download"; fi ;;
    esac
}

offer_install() {
    # offer_install TOOL LABEL WHAT WHY
    local tool="$1" label="$2" what="$3" why="$4" spec level command url
    spec="$(harness_install_command "$tool")"
    level="${spec%%$'\t'*}"; spec="${spec#*$'\t'}"; command="${spec%%$'\t'*}"; url="${spec#*$'\t'}"
    say ""
    say "  $label is not installed."
    say "  What: $what"
    say "  Why: $why"
    if [ "$level" = link ]; then
        say "  There is no package-manager install for it here. Download it from: $url"
        return 1
    fi
    say "  Command: $command"
    if [ "$level" = remote ]; then
        say "  This runs an installer script from the internet in your shell: $url"
        say "  You can read it first: curl -fsSL $url | less"
        [ "$tool" = ollama ] && say "  Ollama's script uses sudo itself, to install to /usr and add a system service."
    fi
    CONFIRM_TOOL="$tool"
    if confirm "$level" n "Install $label now?"; then
        if run_shell "install $label" "$command"; then
            [ "$DRY_RUN" = true ] || { ok "$label installed"; CHANGES=$((CHANGES + 1)); }
            local remove=""
            case "$command" in
                "brew install --cask "*) remove="brew uninstall --cask ${command#brew install --cask }" ;;
                "brew install "*) remove="brew uninstall ${command#brew install }" ;;
                "npm install -g "*) remove="npm uninstall -g ${command#npm install -g }" ;;
                *) remove="see $label's own uninstall instructions" ;;
            esac
            [ "$DRY_RUN" = true ] || helper record --kind package --label "$label" --remove-with "$remove" >/dev/null
            return 0
        fi
    fi
    return 1
}

offer_harness() {
    local primary
    primary="$(answers_value harness)"
    case "$primary" in
        claude-code) have claude && return 0
            offer_install claude-code "Claude Code" "Anthropic's AI coding agent for the terminal." "you chose it as your main AI app." ;;
        codex) have codex && return 0
            offer_install codex "Codex" "OpenAI's AI coding agent for the terminal." "you chose it as your main AI app." ;;
        hermes) have hermes && return 0
            offer_install hermes "Hermes Agent" "Nous Research's agent: memory, skills, scheduled jobs and chat-app gateways. Its own setup wizard runs after it installs." "you chose it as your main AI app." ;;
        openclaw) have openclaw && return 0
            say ""; note "OpenClaw is not installed. Its install guide: https://docs.openclaw.ai/install" ;;
    esac
    return 0
}

install_skills() {
    heading "Adding the Bodhi skill"
    local key label dest action any=false result
    for key in claude-code agents hermes; do
        case "$key" in
            claude-code) have claude || [ "$(answers_value harness)" = claude-code ] || continue
                         label="Claude Code"; dest="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/bodhi-seed" ;;
            agents) { have codex || have openclaw || [ "$(answers_value harness)" = codex ] || [ "$(answers_value harness)" = openclaw ]; } || continue
                    label="Codex and OpenClaw"; dest="$HOME/.agents/skills/bodhi-seed" ;;
            hermes) have hermes || continue
                    install_hermes_skill; any=true; continue ;;
        esac
        any=true
        if [ ! -f "$SEED_DIR/bin/bodhi_install.py" ]; then
            detail "would copy the seed's skill folder to $dest (for $label)"
            continue
        fi
        result="$(helper copy-skill --seed "$SEED_DIR" --target "$key" --dry-run 2>/dev/null)"
        case "$result" in
            *'"unchanged"'*) ok "$label already has the current skill at $dest"; SEED_TARGETS="$SEED_TARGETS $key"; continue ;;
        esac
        local replace=""
        case "$result" in
            *'"exists-unrecorded"'*)
                say "  $label already has a bodhi-seed skill at $dest that this installer did not put there."
                confirm safe n "Replace it with the seed's version?" || { note "left the existing copy alone"; continue; }
                replace="--replace" ;;
            *)
                say "  What: copies the seed's skill folder (text files only) to $dest"
                say "  Why: $label reads personal skills from that folder."
                confirm safe y "Add the Bodhi skill to $label?" || { note "skipped $label"; continue; } ;;
        esac
        SEED_TARGETS="$SEED_TARGETS $key"
        if [ "$DRY_RUN" = true ]; then detail "would copy $SEED_DIR/skills/bodhi-seed to $dest"; continue; fi
        action="$(helper copy-skill --seed "$SEED_DIR" --target "$key" $replace | python3 -c 'import json,sys; print(json.load(sys.stdin)["action"])')"
        ok "$label: skill $action at $dest"
        CHANGES=$((CHANGES + 1))
    done
    [ "$any" = true ] || note "no AI app to add the skill to yet; after installing one, run ./install.sh --update"
}

install_hermes_skill() {
    local current
    current="$(helper targets --seed "$SEED_DIR" | python3 -c 'import json,sys; t=[x for x in json.load(sys.stdin) if x["key"]=="hermes"][0]; print("match" if t["matches"] else ("present" if t["present"] else "none"))')"
    if [ "$current" = match ]; then ok "Hermes already has the current skill"; SEED_TARGETS="$SEED_TARGETS hermes"; return 0; fi
    say "  What: Hermes's own installer copies the seed's skill folder into ~/.hermes/skills."
    say "  Command: hermes skills install $SEED_DIR/skills/bodhi-seed"
    if confirm safe y "Add the Bodhi skill to Hermes?"; then
        if run "hermes skills install" -- hermes skills install "$SEED_DIR/skills/bodhi-seed"; then
            SEED_TARGETS="$SEED_TARGETS hermes"
            [ "$DRY_RUN" = true ] || { ok "Hermes: skill installed"; CHANGES=$((CHANGES + 1));
                helper record --kind hermes-skill --label "Hermes skill bodhi-seed" --remove-with "hermes skills uninstall bodhi-seed" >/dev/null; }
        fi
    else
        note "skipped Hermes"
    fi
}

# ------------------------------------------------------- optional skills ----
# Generalized from the first fleet's own skills. Each is offered once, off by default.
offer_optional_skills() {
    [ -n "$SEED_TARGETS" ] || return 0
    [ -f "$SEED_DIR/bin/bodhi_install.py" ] || return 0
    local list name state about
    list="$(helper optional-skills --seed "$SEED_DIR" --targets "$SEED_TARGETS")" || return 0
    [ -n "$list" ] || return 0
    heading "Optional Bodhi skills (each stays off unless you say yes)"
    say "  Each is one folder of text, added beside the Bodhi skill, and says what it cost the first fleet."
    while IFS='|' read -r name state about; do
        [ -n "$name" ] || continue
        case "$state" in
            current) ok "$name is added and current"; continue ;;
            foreign) note "$name: a copy this installer did not make is already there; left alone"; continue ;;
            stale) confirm safe y "Update the optional skill $name?" || continue ;;
            *) say ""
               say "  $name: $about"
               CONFIRM_TOOL="$name"
               confirm optin n "Add $name?" || continue ;;
        esac
        add_optional_skill "$name"
    done <<SKILLS
$list
SKILLS
}

add_optional_skill() {
    local name="$1" key result action
    for key in $SEED_TARGETS; do
        result="$(helper copy-skill --seed "$SEED_DIR" --target "$key" --skill "$name" --dry-run 2>/dev/null)"
        case "$result" in *'"unchanged"'*) continue ;; esac
        if [ "$key" = hermes ]; then
            if run "hermes skills install $name" -- hermes skills install "$SEED_DIR/skills/$name"; then
                [ "$DRY_RUN" = true ] || { ok "Hermes: $name installed"; CHANGES=$((CHANGES + 1));
                    helper record --kind hermes-skill --label "Hermes skill $name" --remove-with "hermes skills uninstall $name" >/dev/null; }
            fi
            continue
        fi
        case "$result" in *'"exists-unrecorded"'*) note "$name: left a copy this installer did not make ($key)"; continue ;; esac
        if [ "$DRY_RUN" = true ]; then detail "would copy $SEED_DIR/skills/$name beside the Bodhi skill ($key)"; continue; fi
        action="$(helper copy-skill --seed "$SEED_DIR" --target "$key" --skill "$name" | python3 -c 'import json,sys; print(json.load(sys.stdin)["action"])')"
        ok "$name $action ($key)"
        CHANGES=$((CHANGES + 1))
    done
}

offer_gateway() {
    local chat
    chat="$(answers_value chat_app)"
    case "$chat" in telegram|discord|slack|whatsapp|signal|email|teams) ;; *) return 0 ;; esac
    have hermes || { say ""; note "you mentioned $chat: Hermes Agent's gateway can bring Bodhi there (hermes gateway setup), once Hermes is installed"; return 0; }
    if ! input_is_terminal || [ "$YES" = true ]; then
        note "to reach Bodhi in $chat, run: hermes gateway setup (it asks for the app's token itself)"
        return 0
    fi
    say "  Hermes can bring Bodhi into $chat. Its own wizard asks for the app's token; this installer never sees it."
    if confirm safe n "Run hermes gateway setup now?"; then
        hermes gateway setup <&3 || warn "hermes gateway setup did not finish; run it again any time"
    fi
}

# --------------------------------------------------------- optional tools ----
optional_tools() {
    heading "Optional tools (skip any of them)"
    local model notes
    model="$(answers_value model_access)"
    notes="$(answers_value notes_today)"
    if { [ "$model" = local ] || [ "$model" = both ] || in_list ollama; } && ! have ollama; then
        offer_install ollama "Ollama" "runs open models on this computer, with no account." "you said you use local models." || true
    fi
    if { [ "$notes" = obsidian ] || in_list obsidian; } && ! have obsidian && [ ! -d "/Applications/Obsidian.app" ]; then
        offer_install obsidian "Obsidian" "a notes app that keeps plain Markdown files on your computer." "you said your notes live in Obsidian." || true
    fi
    note "LM Studio (local models, with a window): https://lmstudio.ai"
    note "memtrace (a code graph agents query; proprietary beta, link only): https://github.com/syncable-dev/memtrace-public"
}

# ---------------------------------------------------------------- vault ----
offer_vault() {
    heading "Your Bodhi folder (the vault)"
    local path="${VAULT_PATH:-$HOME/Bodhi}"
    if [ -f "$path/context/player_one.json" ]; then ok "your vault is already at $path"; VAULT_PATH="$path"; return 0; fi
    if [ "$YES" = true ] && [ -z "$VAULT_PATH" ]; then
        note "no vault made (unattended). Make one later: python3 $SEED_DIR/bin/bodhi.py init ~/Bodhi"
        return 0
    fi
    if [ -e "$path" ] && [ -n "$(ls -A "$path" 2>/dev/null)" ]; then
        warn "$path exists and is not empty; choose another place with --vault"
        return 0
    fi
    say "  What: a local folder with its own Git history for exact notes, first-session receipts and handoffs."
    say "  Where: $path. Optional: the skill works without it."
    if confirm safe y "Create it?"; then
        if [ "$DRY_RUN" = true ]; then detail "would run: python3 bin/bodhi.py init $path --answers $ANSWERS_FILE"; VAULT_PATH="$path"; return 0; fi
        if python3 "$SEED_DIR/bin/bodhi.py" init "$path" --answers "$ANSWERS_FILE" >> "$LOG_FILE" 2>&1; then
            ok "vault created at $path"
            helper record --kind vault --path "$path" --label "your vault (kept on uninstall)" >/dev/null
            VAULT_PATH="$path"
            CHANGES=$((CHANGES + 1))
        else
            warn "the vault was not created; see $LOG_FILE"
        fi
    fi
}

# --------------------------------------------------------------- finish ----
finish() {
    heading "Checking the result"
    if [ "$DRY_RUN" = true ]; then
        detail "would run: python3 bin/bodhi.py doctor"
        say ""
        say "Dry run: nothing was installed, written or changed."
        return 0
    fi
    local status=0
    if [ -n "$VAULT_PATH" ] && [ -f "$VAULT_PATH/context/player_one.json" ]; then
        python3 "$SEED_DIR/bin/bodhi.py" doctor "$VAULT_PATH" --seed "$SEED_DIR" ${PLAIN_FLAG:+--plain} || status=$?
    else
        python3 "$SEED_DIR/bin/bodhi.py" doctor --seed "$SEED_DIR" ${PLAIN_FLAG:+--plain} || status=$?
    fi
    say ""
    # The seed is planted: a short sprout on a real terminal (bodhi.py mark decides), else nothing.
    if [ -t 1 ] && [ "$NO_TERMINAL" = false ]; then
        if input_is_terminal; then
            python3 "$SEED_DIR/bin/bodhi.py" mark ${PLAIN_FLAG:+--plain} <&3 || true
        else
            python3 "$SEED_DIR/bin/bodhi.py" mark ${PLAIN_FLAG:+--plain} </dev/null || true
        fi
    fi
    if [ "$CHANGES" -eq 0 ]; then say "Nothing needed changing."; else say "Done: $CHANGES change(s)."; fi
    say "Record of what was installed: $BODHI_HOME/install-manifest.json"
    say "Log: $LOG_FILE"
    say "Update later: ./install.sh --update    Remove: ./install.sh --uninstall"
    return $status
}

# ------------------------------------------------------------- uninstall ----
uninstall() {
    heading "Removing what this installer added"
    [ -f "$BODHI_HOME/install-manifest.json" ] || { say "  There is no install record at $BODHI_HOME/install-manifest.json, so there is nothing to remove."; return 0; }
    local seed
    seed="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("seed_dir",""))' "$BODHI_HOME/install-manifest.json")"
    [ -f "$seed/bin/bodhi_install.py" ] || seed="$SCRIPT_DIR"
    [ -f "$seed/bin/bodhi_install.py" ] || die "cannot find the seed's bin/bodhi_install.py; run ./install.sh --uninstall from a clone"
    SEED_DIR="$seed"
    local plan
    plan="$(helper uninstall-plan)"
    printf '%s\n' "$plan" | python3 -c '
import json, sys
plan = json.load(sys.stdin)
for e in plan["remove"]:
    print("  will remove: " + e["path"])
for e in plan["keep"]:
    print("  will keep:   " + e.get("path", e.get("label", "")) + " (" + e["kind"] + ")")
for e in plan["commands"]:
    print("  installed software: " + e["label"] + "; remove with: " + e.get("remove_with", "?"))'
    local commands
    commands="$(printf '%s\n' "$plan" | python3 -c 'import json,sys; [print(e["label"] + "|" + e.get("remove_with","")) for e in json.load(sys.stdin)["commands"]]')"
    if [ -n "$commands" ]; then
        while IFS='|' read -r label remove; do
            case "$remove" in brew\ *|npm\ *|hermes\ skills\ uninstall\ *) ;; *) note "$label: $remove"; continue ;; esac
            if [ "$YES" = true ] && [ "$DRY_RUN" = false ]; then
                note "kept $label (unattended runs never remove software); to remove it: $remove"
                continue
            fi
            if confirm install n "Also remove $label ($remove)?"; then run_shell "remove $label" "$remove" || true; fi
        done <<EOF
$commands
EOF
    fi
    if confirm safe y "Remove the files listed above?"; then
        if [ "$DRY_RUN" = true ]; then helper uninstall-apply --dry-run >/dev/null; detail "would remove the listed files and the install record"; return 0; fi
        helper uninstall-apply >> "$LOG_FILE"
        ok "removed. Kept: your vault, a seed checkout you already had, and the log at $LOG_FILE."
    fi
}

# ----------------------------------------------------------------- main ----
main() {
    if [ "$DRY_RUN" = false ]; then mkdir -p "$BODHI_HOME"; fi
    say "${C_BOLD}Bodhi seed installer${C_OFF} ($MODE$([ "$DRY_RUN" = true ] && echo ', dry run')$([ "$YES" = true ] && echo ', unattended'))"
    [ "$NO_TERMINAL" = true ] && note "no terminal to ask questions in: running unattended with safe defaults"
    say "Nothing is sent anywhere, and no API key is asked for or stored."
    preflight
    if [ "$MODE" = uninstall ]; then uninstall; return $?; fi
    install_prerequisites
    get_seed
    [ "$DRY_RUN" = true ] || [ "$PY_OK" = true ] || die "python3 3.9+ is needed"
    record_seed
    if [ "$MODE" = update ]; then
        heading "Updating the seed"
        if [ -d "$SEED_DIR/.git" ] && confirm safe y "Pull the latest seed into $SEED_DIR?"; then
            run "git pull" -- git -C "$SEED_DIR" pull --ff-only && [ "$DRY_RUN" = false ] && ok "seed is up to date"
        fi
    fi
    setup_questions
    # Setup question 2 names the computer that will hold the Bodhi folder. Plan the
    # tool commands for THAT computer, not for the machine running the installer:
    # people demo the installer from another box, and the tests drive cross-OS
    # plans from answers.json. The scan above stays the host's own report.
    answer_os="$(answers_value os)"
    [ -n "$answer_os" ] && OS_NAME="$answer_os"
    offer_harness
    install_skills
    offer_optional_skills
    offer_gateway
    [ "$MODE" = install ] && optional_tools
    [ "$MODE" = install ] && offer_vault
    finish
}

# Guarded like Hermes's installer, so tests can source the functions without running.
if [ "${BODHI_INSTALL_SOURCE_ONLY:-}" != 1 ]; then
    main
fi
