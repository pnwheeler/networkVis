import requests
import os
import json
import time

# Uncomment to set enviornment variables for OAuth
# command: export 'BEARER_TOKEN'='<your_bearer_token>'

# User fields are adjustable, options include:
# created_at, description, entities, id, location, name,
# pinned_tweet_id, profile_image_url, protected,
# public_metrics, url, username, verified, and withheld

def auth():
    return os.environ.get("BEARER_TOKEN")

def get_input():
    root_acct = input("Enter the name of the account you'd like to analyze: ")
    keywords = input("Enter comma-sep keywords: ")
    # Separate, clean the keywords
    keywords = keywords.split(",")
    for n in range(len(keywords)):
        keywords[n] = keywords[n].strip()
    return(root_acct, keywords)

def create_url(root_acct):
    # Check if root_acct exists as a list--may contain up to 100 usernames
    if(isinstance(root_acct, list)):
        root_acct = ",".join(root_acct)
    usernames = "usernames="+root_acct
    user_fields = "user.fields=id,verified,name,username,description,public_metrics,created_at"
    url = "https://api.twitter.com/2/users/by?{}&{}".format(usernames, user_fields)
    return url

def following_url(acct_id, next_token):
    user_fields = "user.fields=id,username,description,verified"
    max_results = "max_results=1000"
    if (next_token == None):
        return "https://api.twitter.com/2/users/{}/following?{}&{}".format(acct_id, max_results, user_fields)
    else:
        next_page = "pagination_token="+next_token
        return "https://api.twitter.com/2/users/{}/following?{}&{}&{}".format(acct_id, max_results, user_fields, next_page)

def create_headers(bearer_token):
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    return headers

def connect_to_endpoint(url, headers):
    response = requests.request("GET", url, headers=headers)
    print(response.status_code)
    if response.status_code != 200:
        raise Exception(
            "Request returned an error: {} {}".format(
                response.status_code, response.text
            )
        )
    return response.json()

def contains_keyword(s, words):
    for word in words:
        if word in s:
            return True
    return False

def get_following(acct_id, headers, kws):
    following_response = connect_to_endpoint(following_url(acct_id, None), headers)
    following_ids = []
    following_names = []
    if (following_response.get('data') == None):
        return (following_ids, following_names)
    more_results = True
    while(more_results):
        #Get relevant following accts from root
        for i in range(0, len(following_response['data'])):
            relevant = (
                    # Uncomment the following to parse only verified accounts
                    # following_response['data'][i]['verified'] == True
                    contains_keyword(following_response['data'][i]['name'], kws))
            if (relevant):
                following_ids.append(following_response['data'][i]['id'])
                following_names.append(following_response['data'][i]['username'])
        
        # Pagination
        meta_data = following_response['meta']
        if (meta_data.get('next_token') == None):
            more_results = False
        else:
            next_token = meta_data['next_token']
            following_response = connect_to_endpoint(following_url(acct_id, next_token), headers)
    return (following_ids, following_names)

def init_txt(f_name, curr_acct, keywords):
    with open(f_name, 'w') as f:
        f.write("Initial account: %s\n" % (curr_acct))
        f.write("Keywords: ")
        for word in keywords:
            f.write("| %s " % word)
        f.write("|\n") 
    # Create a json file while we're at it
    json_file = ("%s.json" % f_name[:-4])
    f = open(json_file, 'w')
    f.close()    
    return

def write_to_file(json_info, f_name):
    # Write json
    json_file = ("%s.json" % f_name[:-4])
    with open(json_file, 'a') as f:
        json.dump(json_info, f, indent=2)

    with open(f_name, 'a') as f:
        #username, name, description, followers, following, created_at
        for i in range(0, len(json_info['data'])):
            f.write("%s\t%i\t%s\t%s\t%i\t%i\t%s\n" % (json_info['data'][i]['username'],
                                                 json_info['data'][i]['verified'],
                                                 json_info['data'][i]['name'],
                                                 json_info['data'][i]['description'],
                                                 json_info['data'][i]['public_metrics']['followers_count'],
                                                 json_info['data'][i]['public_metrics']['following_count'],
                                                 json_info['data'][i]['created_at']))

    return

def get_acct_info(acct_list, headers, f_name):
    remaining = len(acct_list)
    while (remaining > 0):
        if (remaining >= 100):
            index = 100
        else:
            index = remaining % 100

        results_url = create_url(acct_list[:index])
        results_info = connect_to_endpoint(results_url, headers)
        write_to_file(results_info, f_name)
        acct_list = acct_list[index:]
        remaining -= index

def main():
    bearer_token = auth()
    curr_acct, keywords = get_input()
    f_name = ("%s.txt" % curr_acct)
    init_txt(f_name, curr_acct, keywords)
    url = create_url(curr_acct)
    headers = create_headers(bearer_token)
    json_response = connect_to_endpoint(url, headers)
    # Avoid rate limiting
    time.sleep(61)
    
    init_id = json_response['data'][0]['id']
    root_ids, root_names = get_following(init_id, headers, keywords)
    
    prev_size = len(root_ids)
    num_entries = prev_size
    
    all_names = set()
    all_names.update(root_names)
    all_names.update(curr_acct)

    for i in range(0, num_entries):
        time.sleep(61)
        curr_ids, curr_names = get_following(root_ids[i], headers, keywords)
        all_names.update(curr_names)
        print(len(all_names) - prev_size, " new entries found")
        prev_size = len(all_names)
        print(num_entries - i - 1, " entries remaining")
    
    accts_found = list(all_names)
    get_acct_info(accts_found, headers, f_name)

if __name__ == "__main__":
    main()
