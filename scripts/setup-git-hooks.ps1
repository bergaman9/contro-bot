# CONTRO Bot - Git Hooks Setup Script for Windows
# Sets up automated version control git hooks

param(
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Status
)

$BOT_DIR = $PWD
$GIT_HOOKS_DIR = "$BOT_DIR\.git\hooks"
$SCRIPTS_HOOKS_DIR = "$BOT_DIR\scripts\git-hooks"

function Write-ColoredOutput {
    param($Message, $Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Test-GitRepository {
    if (-not (Test-Path "$BOT_DIR\.git")) {
        Write-ColoredOutput "❌ Error: Not in a git repository" "Red"
        Write-ColoredOutput "Please run this script from the bot directory with git initialized" "Yellow"
        exit 1
    }
    return $true
}

function Test-BotDirectory {
    if (-not (Test-Path "$BOT_DIR\main.py") -or -not (Test-Path "$BOT_DIR\cogs")) {
        Write-ColoredOutput "❌ Error: Not in CONTRO bot directory" "Red"
        Write-ColoredOutput "Please run this script from the bot directory" "Yellow"
        exit 1
    }
    return $true
}

function Install-GitHooks {
    Write-ColoredOutput "🔧 Installing CONTRO Bot Git Hooks..." "Cyan"
    
    # Ensure hooks directory exists
    if (-not (Test-Path $GIT_HOOKS_DIR)) {
        New-Item -ItemType Directory -Path $GIT_HOOKS_DIR -Force | Out-Null
    }
    
    # Install pre-commit hook
    if (Test-Path "$SCRIPTS_HOOKS_DIR\pre-commit") {
        Copy-Item "$SCRIPTS_HOOKS_DIR\pre-commit" "$GIT_HOOKS_DIR\pre-commit" -Force
        Write-ColoredOutput "✅ Installed pre-commit hook" "Green"
    } else {
        Write-ColoredOutput "⚠️  Pre-commit hook script not found" "Yellow"
    }
    
    # Install post-commit hook
    if (Test-Path "$SCRIPTS_HOOKS_DIR\post-commit") {
        Copy-Item "$SCRIPTS_HOOKS_DIR\post-commit" "$GIT_HOOKS_DIR\post-commit" -Force
        Write-ColoredOutput "✅ Installed post-commit hook" "Green"
    } else {
        Write-ColoredOutput "⚠️  Post-commit hook script not found" "Yellow"
    }
    
    # Make hooks executable (Git Bash or WSL)
    if (Get-Command "bash" -ErrorAction SilentlyContinue) {
        bash -c "chmod +x '$GIT_HOOKS_DIR/pre-commit' '$GIT_HOOKS_DIR/post-commit' 2>/dev/null" 2>$null
        Write-ColoredOutput "✅ Made hooks executable" "Green"
    } else {
        Write-ColoredOutput "⚠️  Cannot make hooks executable - ensure Git Bash is available" "Yellow"
    }
    
    Write-ColoredOutput "🎉 Git hooks installation completed!" "Green"
    Write-ColoredOutput "The hooks will now automatically track version changes" "White"
}

function Uninstall-GitHooks {
    Write-ColoredOutput "🗑️  Uninstalling CONTRO Bot Git Hooks..." "Cyan"
    
    $removed = 0
    
    if (Test-Path "$GIT_HOOKS_DIR\pre-commit") {
        Remove-Item "$GIT_HOOKS_DIR\pre-commit" -Force
        Write-ColoredOutput "✅ Removed pre-commit hook" "Green"
        $removed++
    }
    
    if (Test-Path "$GIT_HOOKS_DIR\post-commit") {
        Remove-Item "$GIT_HOOKS_DIR\post-commit" -Force
        Write-ColoredOutput "✅ Removed post-commit hook" "Green"
        $removed++
    }
    
    if ($removed -eq 0) {
        Write-ColoredOutput "ℹ️  No CONTRO Bot hooks found to remove" "Blue"
    } else {
        Write-ColoredOutput "🎉 Git hooks uninstallation completed!" "Green"
    }
}

function Show-Status {
    Write-ColoredOutput "📊 CONTRO Bot Git Hooks Status" "Cyan"
    Write-Host ""
    
    # Check pre-commit hook
    if (Test-Path "$GIT_HOOKS_DIR\pre-commit") {
        Write-ColoredOutput "✅ Pre-commit hook: INSTALLED" "Green"
    } else {
        Write-ColoredOutput "❌ Pre-commit hook: NOT INSTALLED" "Red"
    }
    
    # Check post-commit hook
    if (Test-Path "$GIT_HOOKS_DIR\post-commit") {
        Write-ColoredOutput "✅ Post-commit hook: INSTALLED" "Green"
    } else {
        Write-ColoredOutput "❌ Post-commit hook: NOT INSTALLED" "Red"
    }
    
    # Check version files
    Write-Host ""
    Write-ColoredOutput "📁 Version Control Files:" "Blue"
    
    if (Test-Path "$BOT_DIR\data\versions.json") {
        $versionData = Get-Content "$BOT_DIR\data\versions.json" | ConvertFrom-Json
        $currentVersion = $versionData.current_version
        Write-ColoredOutput "  📄 versions.json: EXISTS (Current: v$currentVersion)" "Green"
    } else {
        Write-ColoredOutput "  📄 versions.json: MISSING" "Red"
    }
    
    if (Test-Path "$BOT_DIR\config\version_config.json") {
        Write-ColoredOutput "  ⚙️  version_config.json: EXISTS" "Green"
    } else {
        Write-ColoredOutput "  ⚙️  version_config.json: MISSING" "Red"
    }
    
    if (Test-Path "$BOT_DIR\CHANGELOG.md") {
        Write-ColoredOutput "  📝 CHANGELOG.md: EXISTS" "Green"
    } else {
        Write-ColoredOutput "  📝 CHANGELOG.md: MISSING" "Red"
    }
    
    # Check last commit tracking
    if (Test-Path "$BOT_DIR\.git\CONTRO_LAST_COMMIT.json") {
        $lastCommit = Get-Content "$BOT_DIR\.git\CONTRO_LAST_COMMIT.json" | ConvertFrom-Json
        Write-Host ""
        Write-ColoredOutput "🔄 Last Tracked Commit:" "Blue"
        Write-ColoredOutput "  Hash: $($lastCommit.last_commit)" "White"
        Write-ColoredOutput "  Time: $($lastCommit.timestamp)" "White"
        Write-ColoredOutput "  Changes: $($lastCommit.significant_changes) significant files" "White"
    }
}

function Show-Help {
    Write-ColoredOutput "🤖 CONTRO Bot - Git Hooks Setup" "Cyan"
    Write-Host ""
    Write-ColoredOutput "USAGE:" "Yellow"
    Write-Host "  .\setup-git-hooks.ps1 -Install     Install git hooks"
    Write-Host "  .\setup-git-hooks.ps1 -Uninstall   Remove git hooks"
    Write-Host "  .\setup-git-hooks.ps1 -Status      Show installation status"
    Write-Host ""
    Write-ColoredOutput "DESCRIPTION:" "Yellow"
    Write-Host "  This script manages automated version control git hooks for CONTRO Bot."
    Write-Host "  The hooks will automatically track code changes and suggest version updates."
    Write-Host ""
    Write-ColoredOutput "FEATURES:" "Yellow"
    Write-Host "  • Pre-commit: Validates version files and suggests updates"
    Write-Host "  • Post-commit: Tracks changes for version management"
    Write-Host "  • Automatic change detection for cogs, utils, and core files"
    Write-Host "  • Integration with Discord bot version commands"
    Write-Host ""
}

# Main script logic
if (-not $Install -and -not $Uninstall -and -not $Status) {
    Show-Help
    exit 0
}

# Validate environment
Test-GitRepository
Test-BotDirectory

if ($Install) {
    Install-GitHooks
} elseif ($Uninstall) {
    Uninstall-GitHooks
} elseif ($Status) {
    Show-Status
}
