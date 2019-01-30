import xbmc
xbmc.executebuiltin('RunScript(special://home/addons/plugin.program.flixstick/default.py,update)')
xbmc.executebuiltin('XBMC.AlarmClock(Notifyloop,XBMC.RunScript(special://home/addons/plugin.program.flixstick/default.py,update),12:00:00,silent,loop)')
