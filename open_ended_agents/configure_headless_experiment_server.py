#!/usr/bin/env python3
"""Patch OneLife for clean headless shutdown and an immortal observer."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys


MARKER = "M10_EXPERIMENT_MODE"
PREVIOUS_MARKER = "M9_EXPERIMENT_MODE"
OLD_MARKER = "M8_HEADLESS_EXPERIMENT_MODE"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one {label} insertion point, found {count}. "
            "No files were changed."
        )
    return text.replace(old, new, 1)


def clean_source_for_upgrade(source: Path) -> str:
    current = source.read_text(encoding="utf-8")
    if MARKER in current:
        return current
    if OLD_MARKER not in current and PREVIOUS_MARKER not in current:
        return current

    # M9's .pre-m9 file can itself contain the earlier M8 patch.  Prefer the
    # clean .pre-m8 source when present, but also support M9 installed directly
    # on a clean checkout, where .pre-m9 is clean.
    candidates = [
        source.with_suffix(source.suffix + ".pre-m8"),
        source.with_suffix(source.suffix + ".pre-m9"),
    ]
    old_backup = next(
        (
            candidate for candidate in candidates
            if candidate.is_file()
            and OLD_MARKER not in candidate.read_text(encoding="utf-8")
            and PREVIOUS_MARKER not in candidate.read_text(encoding="utf-8")
            and MARKER not in candidate.read_text(encoding="utf-8")
        ),
        None,
    )
    if old_backup is None:
        raise RuntimeError(
            "The server contains an older experiment patch, but no clean "
            ".pre-m8 or .pre-m9 backup is available. Restore an unpatched "
            "server.cpp before running M10."
        )
    clean = old_backup.read_text(encoding="utf-8")
    if OLD_MARKER in clean or PREVIOUS_MARKER in clean or MARKER in clean:
        raise RuntimeError(f"The {old_backup.name} backup is not clean.")
    return clean


def patch_server(source: Path) -> Path:
    original_on_disk = source.read_text(encoding="utf-8")
    text = clean_source_for_upgrade(source)
    if MARKER in text:
        print(f"{source} is already configured.")
        return source

    disconnect_anchor = (
        "static void setPlayerDisconnected( LiveObject *inPlayer, \n"
        "                                   const char *inReason ) {    \n"
    )
    disconnect_replacement = (
        f"// {MARKER}\n"
        "static char isHeadlessExperimentAgent( LiveObject *inPlayer ) {\n"
        "    return inPlayer != NULL && inPlayer->email != NULL &&\n"
        "        ( strstr( inPlayer->email, \"+headless-\" ) != NULL ||\n"
        "          strstr( inPlayer->email, \"headless-agent-\" ) ==\n"
        "              inPlayer->email ) &&\n"
        "        SettingsManager::getIntSetting(\n"
        "            \"headlessExperimentMode\", 0 );\n"
        "    }\n\n"
        "static char isImmortalObserver( LiveObject *inPlayer ) {\n"
        "    return inPlayer != NULL && inPlayer->email != NULL &&\n"
        "        ! isHeadlessExperimentAgent( inPlayer ) &&\n"
        "        SettingsManager::getIntSetting(\n"
        "            \"immortalObserverMode\", 0 );\n"
        "    }\n\n\n"
        + disconnect_anchor
        + "    // A stopped headless client is an experiment teardown, not a\n"
        "    // reconnectable human.  Route it through immediate, grave-free\n"
        "    // deletion so no abandoned avatar remains in the world.\n"
        "    if( isHeadlessExperimentAgent( inPlayer ) ) {\n"
        "        setDeathReason( inPlayer, \"headless_stop\" );\n"
        "        inPlayer->customGraveID = 0;\n"
        "        inPlayer->error = true;\n"
        "        inPlayer->errorCauseString = \"Headless runner stopped\";\n"
        "        }\n"
    )
    text = replace_once(
        text, disconnect_anchor, disconnect_replacement, "disconnect cleanup"
    )

    age_anchor = (
        "double computeAge( LiveObject *inPlayer ) {\n"
        "    double age = computeAge( inPlayer->lifeStartTimeSeconds );\n"
    )
    age_replacement = (
        "static char isHeadlessExperimentAgent( LiveObject *inPlayer );\n"
        "static char isImmortalObserver( LiveObject *inPlayer );\n\n\n"
        + age_anchor
        + "\n"
        "    if( ( isHeadlessExperimentAgent( inPlayer ) ||\n"
        "          isImmortalObserver( inPlayer ) ) &&\n"
        "        age >= forceDeathAge ) {\n"
        "        return forceDeathAge - 0.001;\n"
        "        }\n"
    )
    text = replace_once(text, age_anchor, age_replacement, "old-age guard")

    harm_anchor = (
        "            if( nextPlayer->dying && ! nextPlayer->error &&\n"
        "                curTime >= nextPlayer->dyingETA ) {\n"
    )
    harm_replacement = (
        "            // Keep active experiment avatars out of lethal states.\n"
        "            if( ( isHeadlessExperimentAgent( nextPlayer ) ||\n"
        "                  isImmortalObserver( nextPlayer ) ) &&\n"
        "                nextPlayer->connected &&\n"
        "                ( nextPlayer->error || nextPlayer->dying ) ) {\n"
        "                nextPlayer->error = false;\n"
        "                nextPlayer->dying = false;\n"
        "                nextPlayer->dyingETA = 0;\n"
        "                }\n\n"
        + harm_anchor
    )
    text = replace_once(text, harm_anchor, harm_replacement, "lethal-state guard")

    decrement_anchor = (
        "                    if( !heldByFemale ) {\n\n"
        "                        if( nextPlayer->yummyBonusStore > 0 ) {\n"
    )
    decrement_replacement = (
        "                    if( !heldByFemale ) {\n\n"
        "                        // The graphical observer is outside the\n"
        "                        // experiment: its hunger bar never decreases.\n"
        "                        if( isImmortalObserver( nextPlayer ) ) {\n"
        "                            nextPlayer->foodDecrementETASeconds =\n"
        "                                curTime + 3600;\n"
        "                            }\n"
        "                        else if( nextPlayer->yummyBonusStore > 0 ) {\n"
    )
    text = replace_once(
        text, decrement_anchor, decrement_replacement, "observer hunger guard"
    )

    food_eta_anchor = (
        "                    nextPlayer->foodDecrementETASeconds = curTime +\n"
        "                        computeFoodDecrementTimeSeconds( nextPlayer );\n"
    )
    food_eta_replacement = (
        "                    if( isImmortalObserver( nextPlayer ) ) {\n"
        "                        nextPlayer->foodDecrementETASeconds =\n"
        "                            curTime + 3600;\n"
        "                        }\n"
        "                    else {\n"
        + food_eta_anchor
        + "                        }\n"
    )
    text = replace_once(
        text, food_eta_anchor, food_eta_replacement,
        "observer food-timer guard"
    )

    hunger_anchor = (
        "                    if( decrementedPlayer != NULL &&\n"
        "                        decrementedPlayer->foodStore < 0 ) {\n"
    )
    hunger_replacement = (
        "                    // Headless hunger remains observable but cannot\n"
        "                    // kill the active experimental learner.\n"
        "                    if( decrementedPlayer != NULL &&\n"
        "                        decrementedPlayer->foodStore < 0 &&\n"
        "                        isHeadlessExperimentAgent( decrementedPlayer ) ) {\n"
        "                        decrementedPlayer->foodStore = 0;\n"
        "                        decrementedPlayer->updateGlobal = true;\n"
        "                        decrementedPlayer = NULL;\n"
        "                        }\n\n"
        + hunger_anchor
    )
    text = replace_once(text, hunger_anchor, hunger_replacement, "starvation guard")

    delete_eta_anchor = (
        "                nextPlayer->deleteSentDoneETA = Time::getCurrentTime() + 10;\n"
    )
    delete_eta_replacement = (
        delete_eta_anchor
        + "                if( isHeadlessExperimentAgent( nextPlayer ) ) {\n"
        "                    nextPlayer->deleteSentDoneETA = 0;\n"
        "                    }\n"
    )
    text = replace_once(
        text, delete_eta_anchor, delete_eta_replacement, "immediate teardown"
    )
    trigger_anchor = (
        "                if( areTriggersEnabled() ) {\n"
        "                    // add extra time so that rest of triggers can be received\n"
    )
    trigger_replacement = (
        "                if( areTriggersEnabled() &&\n"
        "                    ! isHeadlessExperimentAgent( nextPlayer ) ) {\n"
        "                    // add extra time so that rest of triggers can be received\n"
    )
    text = replace_once(
        text, trigger_anchor, trigger_replacement, "headless trigger bypass"
    )

    backup = source.with_suffix(source.suffix + ".pre-m9")
    if not backup.exists():
        backup.write_text(original_on_disk, encoding="utf-8")
        shutil.copystat(source, backup)
    source.write_text(text, encoding="utf-8")
    return backup


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-cpp", default="server/server.cpp")
    args = parser.parse_args()
    source = Path(args.server_cpp).expanduser().resolve()
    if not source.is_file():
        print(f"Not found: {source}", file=sys.stderr)
        return 2
    try:
        backup = patch_server(source)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"Configured {source}")
    print(f"Backup: {backup}")
    print(
        "Next: mkdir -p server/settings && "
        "echo 1 > server/settings/headlessExperimentMode.ini && "
        "echo 1 > server/settings/immortalObserverMode.ini && make -C server"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
