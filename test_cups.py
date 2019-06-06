import cups

conn = cups.Connection()
printers = conn.getPrinters()
default_printer = printers.keys()[0]
cups.setUser('pi')
conn.printFile (default_printer, fileName, "boothy", {'fit-to-page':'True'})

