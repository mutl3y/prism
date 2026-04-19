# FindMousePointer.ahk

AutoHotkey v2 script for Windows 10 that:

- highlights the mouse pointer where it already is
- moves the mouse pointer to the center of the primary screen
- shows a large bright visual marker around it
- runs from hotkeys so you can trigger it quickly

## Default hotkeys

The script uses two hotkeys:

```text
Ctrl + Alt + H  = highlight the pointer where it is now
Ctrl + Alt + M
```

These lines define them:

```ahk
^!h::HighlightCurrentPointer()
^!m::CenterMouseAndHighlight()
```

If you want different hotkeys, change those lines.

## How to use it

1. Save `FindMousePointer.ahk` somewhere on your Windows machine.
2. Double-click it to run it with AutoHotkey.
3. Press `Ctrl + Alt + H` to highlight the current pointer location.
4. Press `Ctrl + Alt + M` to move the pointer to the screen center and highlight it there.

The marker will appear briefly around the pointer in either mode.

## Easy tweaks

The current version uses a cleaner circular target marker with:

- a large outer ring
- a smaller inner ring
- small cardinal tick marks
- a bright center dot
- black shadow layers for contrast

Inside the script, these are the easiest settings to tune:

```ahk
accentColor := "00FFFF"
shadowColor := "000000"
durationMs := 950
```
