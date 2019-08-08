import os
import sys
import json
import requests
from github3 import login

POST_URL = 'https://slack.com/api/chat.postMessage'

BLOCKED_LABEL = 'BLOCKED'

ignore = os.environ.get('IGNORE_WORDS')
IGNORE_WORDS = [i.lower().strip() for i in ignore.split(',')] if ignore else []

repositories = os.environ.get('REPOSITORIES')
REPOSITORIES = [r.lower().strip() for r in repositories.split(',')] if repositories else []

usernames = os.environ.get('USERNAMES')
USERNAMES = [u.lower().strip() for u in usernames.split(',')] if usernames else []

SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', 'peya_automation')

MIN_OF_REVIEW = os.environ.get('MIN_OF_REVIEW', 0)

try:
    SLACK_API_TOKEN = os.environ['SLACK_API_TOKEN']
    GITHUB_API_TOKEN = os.environ['GITHUB_API_TOKEN']
    ORGANIZATION = os.environ['ORGANIZATION']
except KeyError as error:
    sys.stderr.write('Please set the environment variable {0}'.format(error))
    sys.exit(1)


def fetch_repository_pulls(repository):
    pulls = []
    for pull in repository.pull_requests():
        if pull.state == 'open' and (not USERNAMES or pull.user.login.lower() in USERNAMES):
            pulls.append(pull)
    return pulls


def is_valid_title(title):
    lowercase_title = title.lower()
    for ignored_word in IGNORE_WORDS:
        if ignored_word in lowercase_title:
            return False

    return True


def as_label(pull, text):
    for label in pull.labels:
        if str(label['name']).upper() == text:
            return True
    return False


def count_pull_request_reviews(pull_request):
    count = 0

    reviews = {}

    for r in pull_request.reviews():
        if r.state != 'COMMENTED':
            reviews[r.user.login] = r.state

    for r_user in reviews:
        if reviews[r_user] == 'APPROVED':
            count += 1

    result = {
        'APPROVED': 0,
        'CHANGES_REQUESTED': 0,
        'PENDING': 0
    }

    for _, value in reviews.items():
        if value in ['APPROVED', 'CHANGES_REQUESTED', 'PENDING']:
            result[value] = result[value] + 1

    return result


def format_pull_requests(pull_requests, owner, repository):
    lines = []

    for pull in pull_requests:
        if is_valid_title(pull.title):
            creator = pull.user.login
            text = ' » *[{0}/{1}]* <{2}|{3} - by {4}>'.format(
                owner, repository, pull.html_url, pull.title, creator)
            lines.append({
                "text": text,
                "is_blocked": as_label(pull, BLOCKED_LABEL),
                "reviews": count_pull_request_reviews(pull)
            })

    return lines


def fetch_organization_pulls(organization_name):
    """
    Returns a formatted string list of open pull request messages.
    """
    client = login(token=GITHUB_API_TOKEN)
    organization = client.organization(organization_name)
    lines = []

    for repository in organization.repositories():
        if REPOSITORIES and repository.name.lower() not in REPOSITORIES:
            continue
        unchecked_pulls = fetch_repository_pulls(repository)
        lines += format_pull_requests(unchecked_pulls, organization_name,
                                      repository.name)

    return lines


def send_to_slack(ready_to_merge=[], waiting_for_aprobals=[], changes_needed=[], blockeds=[]):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "🚧 *Open Pull Requests Waiting for Merge* 🚧"
            }
        }
    ]

    if len(ready_to_merge) > 0:
        blocks.append({
            "type": "divider"
        })

        lines = ''

        for pr in ready_to_merge:
            lines += '\n' + pr['text']

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Ready to Merge:*" + lines
            }
        })

    if len(waiting_for_aprobals) > 0:
        blocks.append({
            "type": "divider"
        })

        lines = ''

        for pr in waiting_for_aprobals:
            lines += '\n' + pr['text']

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Waiting for aprobals:*" + lines
            }
        })

    if len(changes_needed) > 0:
        blocks.append({
            "type": "divider"
        })

        lines = ''

        for pr in changes_needed:
            lines += '\n' + pr['text']

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Changes Needed:*" + lines
            }
        })

    if len(blockeds) > 0:
        blocks.append({
            "type": "divider"
        })

        lines = ''

        for pr in blockeds:
            lines += '\n' + pr['text']

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Blockeds:*" + lines
            }
        })

    payload = {
        'token': SLACK_API_TOKEN,
        'channel': SLACK_CHANNEL,
        'as_user': False,
        'blocks': json.dumps(blocks)
    }

    response = requests.post(POST_URL, data=payload)
    answer = response.json()
    if not answer['ok']:
        print(answer)
        raise Exception(answer['error'])


def cli():
    pull_requests = fetch_organization_pulls(ORGANIZATION)

    blockeds = []
    ready_to_merge = []
    waiting_for_aprobals = []
    changes_needed = []

    for pr in pull_requests:
        if pr['is_blocked']:
            blockeds.append(pr)
        else:
            if pr['reviews']['CHANGES_REQUESTED'] > 0:
                changes_needed.append(pr)
            elif pr['reviews']['APPROVED'] >= MIN_OF_REVIEW:
                ready_to_merge.append(pr)
            else:
                waiting_for_aprobals.append(pr)

    send_to_slack(ready_to_merge, waiting_for_aprobals, changes_needed, blockeds)


if __name__ == '__main__':
    cli()
