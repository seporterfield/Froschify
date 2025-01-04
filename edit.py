from moviepy import VideoFileClip, concatenate_videoclips


def insert_clip_in_middle(video: VideoFileClip, clip: VideoFileClip) -> VideoFileClip:
    first_half = video.subclipped(0, video.duration / 2)
    second_half = video.subclipped(video.duration / 2)

    return concatenate_videoclips([first_half, clip, second_half], method="compose")
