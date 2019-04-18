# Pull Request Reminder

>Posts a Slack reminder with a list of open pull requests for an organization.


## Installation

```Bash
    $ pip install slack-pull-reminder
```

## Usage

slack-pull-reminder is configured using environment variables:

**Required:**

-  ``SLACK_API_TOKEN``
-  ``GITHUB_API_TOKEN``
-  ``ORGANIZATION``: The GitHub organization you want pull request
   reminders for.

**Optional**

-  ``IGNORE_WORDS``: A comma-separated list of words that will cause a pull request to be ignored.

-  ``REPOSITORIES``: A comma-separated list of repository names to check, where all other repositories in the organization are ignored. All repositories are checked by default.

-  ``USERNAMES``: A comma-separated list of GitHub usernames to filter pull requests by, where all other users are ignored. All users in the organization are included by default.

-  ``SLACK_CHANNEL``: The Slack channel you want the reminders to be posted in, defaults to #general.

Cronjob


As slack-pull-reminder only runs once and exits, it's recommended to run
it regularly using for example a cronjob.

Example that runs slack-pull-reminder every day at 10:00:

```Bash
    0 10 * * * ORGANIZATION="orgname" SLACK_API_TOKEN="token" GITHUB_API_TOKEN="token" slack-pull-reminder
```