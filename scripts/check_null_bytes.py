import os
import sys
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
count=0
for dirpath, dirs, files in os.walk(root):
    for f in files:
        if f.endswith('.py'):
            p=os.path.join(dirpath,f)
            b=open(p,'rb').read()
            if b.find(b'\x00')!=-1:
                print('NULL in', p)
                count+=1
print('DONE', count)
