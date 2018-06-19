from sys import argv
import http.server
import os, sys

WEB_PORT = 65500

if len(argv) >= 2:
    port_str = str(argv[1])
    if port_str.isdecimal() == True:
        port = int(port_str)
        if port > 1024 and port <= 65535:
            WEB_PORT = port
            print('Port {} used'.format(WEB_PORT))
        else:
            print('Out of port range (1025-65535)')
            print('Default port {} used'.format(WEB_PORT))
    else:
        print('Out of port range (1025-65535)')
        print('Default port {} used'.format(WEB_PORT))
else:
    print('Default port {} used'.format(WEB_PORT))
    print('"python3.6 screenmonitor.py port" to set port')

server_address = ("", WEB_PORT)
handler_class = http.server.SimpleHTTPRequestHandler
screen_monitor = http.server.HTTPServer(server_address, handler_class)
screen_monitor.serve_forever()
