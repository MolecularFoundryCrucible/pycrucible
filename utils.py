import subprocess as sp
import hashlib
import pytz
from datetime import datetime

def run_shell(cmd, checkflag = True, background = False):
    if background:
        return(sp.Popen(cmd, stdout = sp.PIPE, stderr = sp.STDOUT, shell = True, universal_newlines = True))
    return(sp.run(cmd, stdout = sp.PIPE, stderr = sp.STDOUT, shell = True, universal_newlines = True, check = checkflag))


def checkhash(file):
    with open(file,"rb") as f:
        fdata = f.read() 
        readable_hash = hashlib.sha256(fdata).hexdigest()
    return(readable_hash)

    
def get_tz_isoformat(timezone = "America/Los_Angeles"):
    pst= pytz.timezone(timezone)
    curr_pct_time = datetime.now(pst).isoformat()
    return(curr_pct_time)









