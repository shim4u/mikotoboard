To Install: drop it somewhere on your server.<br>
To Use: Run views.py. Uses port 6060. Then set up some proxy, i.e. like here http://www.tornadoweb.org/documentation/overview.html?highlight=nginx#running-tornado-in-production<br>
Or, you can just change application port to 80 and start script as root, your choice, really.
Requirements: TornadoWeb, Python Imaging Library, Mongodb, pymogno, python2.<br>
<font color="red">WARNING!</font> this script makes use of asynchronous featuers of tornado web.<br>
Oh, and by the way, there's a lot of russian language used. You'll have to translate it yourself, by now. I'll add internationalization later, someday.
