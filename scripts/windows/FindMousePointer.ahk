#Requires AutoHotkey v2.0
#SingleInstance Force

CoordMode "Mouse", "Screen"

^!h::HighlightCurrentPointer()
^!m::CenterMouseAndHighlight()

CenterMouseAndHighlight() {
    centerX := A_ScreenWidth // 2
    centerY := A_ScreenHeight // 2

    MouseMove centerX, centerY, 0
    ShowPointerMarker(centerX, centerY)
}

HighlightCurrentPointer() {
    MouseGetPos &mouseX, &mouseY
    ShowPointerMarker(mouseX, mouseY)
}

ShowPointerMarker(x, y) {
    markerParts := []

    accentColor := "00FFFF"
    shadowColor := "000000"
    durationMs := 950

    markerParts.Push(MakeCircularRing(x, y, 232, 14, shadowColor, 150))
    markerParts.Push(MakeCircularRing(x, y, 216, 8, accentColor, 235))
    markerParts.Push(MakeCircularRing(x, y, 116, 10, shadowColor, 150))
    markerParts.Push(MakeCircularRing(x, y, 102, 6, accentColor, 250))

    markerParts.Push(MakeMarkerPiece(x - 4, y - 128, 8, 24, shadowColor, 150))
    markerParts.Push(MakeMarkerPiece(x - 3, y - 124, 6, 18, accentColor, 245))
    markerParts.Push(MakeMarkerPiece(x - 4, y + 104, 8, 24, shadowColor, 150))
    markerParts.Push(MakeMarkerPiece(x - 3, y + 106, 6, 18, accentColor, 245))
    markerParts.Push(MakeMarkerPiece(x - 128, y - 4, 24, 8, shadowColor, 150))
    markerParts.Push(MakeMarkerPiece(x - 124, y - 3, 18, 6, accentColor, 245))
    markerParts.Push(MakeMarkerPiece(x + 104, y - 4, 24, 8, shadowColor, 150))
    markerParts.Push(MakeMarkerPiece(x + 106, y - 3, 18, 6, accentColor, 245))

    markerParts.Push(MakeFilledCircle(x, y, 24, shadowColor, 165))
    markerParts.Push(MakeFilledCircle(x, y, 14, accentColor, 255))

    SetTimer DestroyMarker.Bind(markerParts), -durationMs
}

MakeMarkerPiece(x, y, width, height, color, opacity) {
    overlay := Gui("+AlwaysOnTop -Caption +ToolWindow +E0x20 +LastFound")
    overlay.BackColor := color
    overlay.Show(Format("x{} y{} w{} h{} NoActivate", x, y, width, height))
    WinSetTransparent opacity, "ahk_id " overlay.Hwnd
    return overlay
}

MakeCircularRing(centerX, centerY, diameter, thickness, color, opacity) {
    overlay := Gui("+AlwaysOnTop -Caption +ToolWindow +E0x20 +LastFound")
    overlay.BackColor := color

    left := centerX - (diameter // 2)
    top := centerY - (diameter // 2)

    overlay.Show(Format("x{} y{} w{} h{} NoActivate", left, top, diameter, diameter))

    outerRegion := DllCall("Gdi32.dll\CreateEllipticRgn", "Int", 0, "Int", 0, "Int", diameter, "Int", diameter, "Ptr")
    innerInset := thickness
    innerDiameter := diameter - (innerInset * 2)

    if (innerDiameter > 0) {
        innerRegion := DllCall(
            "Gdi32.dll\CreateEllipticRgn",
            "Int", innerInset,
            "Int", innerInset,
            "Int", innerInset + innerDiameter,
            "Int", innerInset + innerDiameter,
            "Ptr"
        )
        ringRegion := DllCall("Gdi32.dll\CreateRectRgn", "Int", 0, "Int", 0, "Int", 1, "Int", 1, "Ptr")
        DllCall("Gdi32.dll\CombineRgn", "Ptr", ringRegion, "Ptr", outerRegion, "Ptr", innerRegion, "Int", 4)
        DllCall("Gdi32.dll\DeleteObject", "Ptr", outerRegion)
        DllCall("Gdi32.dll\DeleteObject", "Ptr", innerRegion)
    } else {
        ringRegion := outerRegion
    }

    DllCall("User32.dll\SetWindowRgn", "Ptr", overlay.Hwnd, "Ptr", ringRegion, "Int", true)
    WinSetTransparent opacity, "ahk_id " overlay.Hwnd
    return overlay
}

MakeFilledCircle(centerX, centerY, diameter, color, opacity) {
    overlay := Gui("+AlwaysOnTop -Caption +ToolWindow +E0x20 +LastFound")
    overlay.BackColor := color

    left := centerX - (diameter // 2)
    top := centerY - (diameter // 2)

    overlay.Show(Format("x{} y{} w{} h{} NoActivate", left, top, diameter, diameter))

    circleRegion := DllCall("Gdi32.dll\CreateEllipticRgn", "Int", 0, "Int", 0, "Int", diameter, "Int", diameter, "Ptr")
    DllCall("User32.dll\SetWindowRgn", "Ptr", overlay.Hwnd, "Ptr", circleRegion, "Int", true)
    WinSetTransparent opacity, "ahk_id " overlay.Hwnd
    return overlay
}

DestroyMarker(markerParts) {
    for _, overlay in markerParts {
        try overlay.Destroy()
    }
}
