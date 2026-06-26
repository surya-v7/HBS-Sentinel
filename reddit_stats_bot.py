import praw
import os
import time
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log"),
    ],
)
log = logging.getLogger(__name__)


def get_account_age(created_utc: float) -> str:
    """Return a human-readable account age string."""
    created = datetime.fromtimestamp(created_utc, tz=timezone.utc)
    delta = datetime.now(tz=timezone.utc) - created
    days = delta.days

    if days < 30:
        return f"{days} day{'s' if days != 1 else ''}"
    elif days < 365:
        months = days // 30
        return f"~{months} month{'s' if months != 1 else ''}"
    else:
        years = days // 365
        months = (days % 365) // 30
        if months:
            return f"{years} year{'s' if years != 1 else ''}, {months} month{'s' if months != 1 else ''}"
        return f"{years} year{'s' if years != 1 else ''}"


def build_stats_comment(author) -> str:
    age = get_account_age(author.created_utc)
    total_karma = author.link_karma + author.comment_karma

    lines = [
        f"📊 **Account Stats for u/{author.name}**",
        "",
        f"| Stat | Value |",
        f"|------|-------|",
        f"| 📝 Post Karma | {author.link_karma:,} |",
        f"| 💬 Comment Karma | {author.comment_karma:,} |",
        f"| ⭐ Total Karma | {total_karma:,} |",
        f"| 🎂 Account Age | {age} |",
        "",
        "^(I am a bot. This comment is posted automatically on every new submission.)",
    ]
    return "\n".join(lines)


def run_bot():
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "AccountStatsBot/1.0"),
    )

    subreddit_name = os.getenv("SUBREDDIT_NAME")
    if not subreddit_name:
        raise ValueError("SUBREDDIT_NAME is not set in your .env file.")

    subreddit = reddit.subreddit(subreddit_name)
    log.info(f"Bot started. Monitoring r/{subreddit_name} for new submissions...")

    while True:
        try:
            for submission in subreddit.stream.submissions(skip_existing=True):
                author = submission.author

                # Skip deleted/suspended accounts
                if author is None:
                    log.warning(f"Skipping post {submission.id} — author unavailable.")
                    continue

                log.info(f"New post by u/{author.name}: '{submission.title[:60]}'")

                comment_body = build_stats_comment(author)
                comment = submission.reply(comment_body)

                # Optional: distinguish the comment (requires mod privileges)
                # comment.mod.distinguish(how="yes", sticky=True)

                log.info(f"Replied with stats for u/{author.name}")

                # Be polite to the API — avoid rate limiting
                time.sleep(2)

        except praw.exceptions.APIException as e:
            log.error(f"Reddit API error: {e}. Waiting 60s before retrying...")
            time.sleep(60)
        except Exception as e:
            log.error(f"Unexpected error: {e}. Waiting 30s before retrying...")
            time.sleep(30)


if __name__ == "__main__":
    run_bot()
