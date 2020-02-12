from fabric import SerialGroup

result = SerialGroup('host1','host2','host3','host4','host5').run('hostname')


