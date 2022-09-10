# Readme

## How it works

- BBot.py uses the .env file to get important info such as which roles/users it considers important (Super roles/users), the server it is on, the channel it sends the "happy birthday" message to etc.  
- We run an infinte loop which checks if it is someones birthday ever x hours (this will probably be 24 hours on production).

- It allows any user to add their birthday if it not already in the list. It only allows super users/roles to remove a birthday so that normal users can't keep changing their birthday. Super users/roles can also set other peoples birthdays for them. 

- We can manually run the birthday check function by running @bbot wish
 