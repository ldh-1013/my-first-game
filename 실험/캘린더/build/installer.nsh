; Uninstall cleanup for the "check todos at login" option.
; If the option was on when the app is removed, the Run entry would keep pointing
; at an exe that no longer exists. The value name is the app id (APP_ID in main.cjs).
!macro customUnInstall
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "com.zrcsh.mycalendar"
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run" "com.zrcsh.mycalendar"
!macroend
