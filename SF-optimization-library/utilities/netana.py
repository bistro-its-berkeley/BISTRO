import pandas as pd

csvfile =  open("network.csv")
df = pd.read_csv(csvfile, index_col = 0)
print(df)

#X
print("XMIN ", min(list(df['toLocationX']) + list(df['fromLocationX'])))
print("XMAX ", max(list(df['toLocationX']) + list(df['fromLocationX'])))

#Y
print("YMIN ", min(list(df['toLocationY']) + list(df['fromLocationY'])))
print("YMAX ", max(list(df['toLocationY']) + list(df['fromLocationY'])))