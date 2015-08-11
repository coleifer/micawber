import pprint
from micawber import bootstrap_embedly, ProviderException
try:
    input = raw_input
except NameError:
    pass

def main():
    print('Please wait, loading providers from embed.ly')
    providers = bootstrap_embedly()

    while 1:
        url = input('Enter a url (or q to quit): ')
        if url.lower().strip() == 'q':
            break

        try:
            result = providers.request(url)
        except ProviderException:
            print('No provider found for that url :/')
        else:
            print('Data for %s\n====================================================' % url)
            pprint.pprint(result)

if __name__ == '__main__':
    print('Welcome to the example!')
    main()
