# STAGE 1.3
#python task_3.py
from appworld import AppWorld

task_id = "692c77d_2" # Give a 1-star rating to all songs in my Spotify song library which I have not liked. If I have already rated it higher, decrease it to 1.

with AppWorld(task_id=task_id, experiment_name="manual") as world:
    print("task:", world.task.instruction)
    world.execute("email = apis.supervisor.show_profile()['email']")
    world.execute("passwords = apis.supervisor.show_account_passwords()")
    world.execute("password = [p['password'] for p in passwords if p['account_name'] == 'spotify'][0]")
    world.execute("token = apis.spotify.login(username=email, password=password)['access_token']")

    world.execute("library = []")
    world.execute("""
    for page in range(20):
        lib = apis.spotify.show_song_library(access_token=token, page_index=page, page_limit=20)
        if not lib:
            break
        library.extend(lib)
    """)

    world.execute("lib_song_ids = set()")
    world.execute("""
    for song in library:
        lib_song_ids.add(song['song_id'])
    """)

    world.execute("liked = []")
    world.execute("""
    for p in range(20):
        like = apis.spotify.show_liked_songs(access_token=token, page_index=p, page_limit=20)
        if not like:
            break
        liked.extend(like)
    """)

    world.execute("liked_song_ids = set()")
    world.execute("""
    for a_song in liked:
        liked_song_ids.add(a_song['song_id'])
    """)

    world.execute("to_rate = lib_song_ids - liked_song_ids")
    print(world.execute("print(to_rate)"))

    world.execute("rs = []")
    world.execute("""
    for rev_song in to_rate:
        for rp in range(20):
            review = apis.spotify.show_song_reviews(song_id=rev_song, user_email=email, page_index=rp, page_limit=20)
            if not review:
                break
            rs.extend(review)
    """)
    print(world.execute("print(rs)"))

    world.execute("reviewed = {}")
    world.execute("""
    for a_rs in rs:
        reviewed[a_rs['song_id']] = a_rs['song_review_id']
    """)
    print(world.execute("print(reviewed)"))

    world.execute("""
    for rate_song in to_rate:
        if rate_song in reviewed:
            apis.spotify.update_song_review(access_token=token, rating=1, review_id=reviewed[rate_song])
        else:
            apis.spotify.review_song(song_id=rate_song, access_token=token, rating=1)
    """)

    world.execute("after_upd = []")
    world.execute("""
    for rev_song in to_rate:
        for rp in range(20):
            review = apis.spotify.show_song_reviews(song_id=rev_song, user_email=email, page_index=rp, page_limit=20)
            if not review:
                break
            after_upd.extend(review)
    """)
    print(world.execute("print(after_upd)"))

    world.execute("apis.supervisor.complete_task()")
    print(world.evaluate())