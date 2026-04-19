import os
import time
import requests

def post_to_threads(text_content):
    """
    Posts text content to Meta Threads via the official Graph API.
    """
    threads_user_id = os.getenv("THREADS_USER_ID")
    access_token = os.getenv("THREADS_ACCESS_TOKEN")

    if not threads_user_id or not access_token:
        print("⚠️ Missing Threads credentials (THREADS_USER_ID or THREADS_ACCESS_TOKEN). Skipping Threads post.")
        return False

    print("🧵 Preparing to post to Threads...")
    
    # Check limit (500 characters)
    if len(text_content) > 500:
        print("⚠️ Content exceeds 500 chars. Truncating...")
        text_content = text_content[:496] + "..."

    # Step 1: Create Media Container
    # Hint: If threads_user_id is invalid, try using 'me'
    target_id = threads_user_id if threads_user_id and threads_user_id.lower() != "none" else "me"
    create_container_url = f"https://graph.threads.net/v1.0/{target_id}/threads"
    
    payload = {
        "media_type": "TEXT",
        "text": text_content,
        "access_token": access_token
    }

    try:
        print(f"  Attempting to post with ID: {target_id}")
        res = requests.post(create_container_url, data=payload)
        res_data = res.json()
        
        if "error" in res_data:
            error_msg = res_data['error'].get('message', 'Unknown error')
            print(f"❌ Failed to create Threads container: {error_msg}")
            if "ID" in error_msg:
                print("💡 Tip: Your THREADS_USER_ID might be wrong. Try setting it to 'me' in GitHub Secrets.")
            return False
            
        creation_id = res_data.get("id")
        print(f"  ✔️ Container created (ID: {creation_id}). Publishing...")
        
        # Mandatory wait for server readiness
        time.sleep(3)

        # Step 2: Publish the container
        publish_url = f"https://graph.threads.net/v1.0/{target_id}/threads_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": access_token
        }
        
        pub_res = requests.post(publish_url, data=publish_payload)
        pub_data = pub_res.json()
        
        if "id" in pub_data:
            print(f"✅ Threads post successful! ID: {pub_data['id']}")
            return True
        else:
            print(f"❌ Threads publish failed: {pub_data}")
            return False

    except Exception as e:
        print(f"❌ Error during Threads post: {e}")
        return False

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    post_to_threads("Test post from Hungary Daily Insider! ✨")
