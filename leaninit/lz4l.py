import os
import logging 
import subprocess
import shutil
import tempfile

lz4 = shutil.which('lz4')

def invoke_tool(*cmd) -> str:
    out=[]
    try:
        res=subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        outstr = res.stdout.decode()
        logging.debug(outstr)
        logging.debug(res.stderr.decode())
    except subprocess.CalledProcessError as e:
        nl = '\n'
        logging.debug(f'{cmd[0]} failed')
        logging.debug(f'arguments: {str(e.args)}')
        logging.debug(f'stdout{nl}{e.stdout}')
        logging.debug(f'stderr{nl}{e.stderr}')
        logging.debug(f'return code: {e.returncode}')
        raise
    return outstr

def get_tmp_file() -> str:
    file = os.path.join(tempfile.mkdtemp(), 'lz4l.tmp')
    return file

def compress(data: bytes,*,lz4_path: str|None = None) -> bytes:
    if lz4_path is None:
        if lz4 is None:
            raise RuntimeError('could not find lz4')
        lz4_path = lz4
    tmpfile = get_tmp_file()
    with open(tmpfile,'wb') as f:
        f.write(data)
    outfile = get_tmp_file()
    invoke_tool(lz4_path,'-9','-l','-f',tmpfile,outfile)
    out = open(outfile,'rb').read()
    os.remove(outfile)
    return out
