import pandas
data = pandas.read_excel('data.xlsx')
year = data['date'].astype(str).apply(lambda x: x.split('-')[0])

if __name__ == "__main__":
    print(year)

