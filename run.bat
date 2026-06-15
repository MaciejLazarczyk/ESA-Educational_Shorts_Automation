@echo on
set "BASE=%~dp0"

del /s /q "%BASE%\ReadyContent\readyArticles\*"
del /s /q "%BASE%\ReadyContent\readyDescriptions\*"
del /s /q "%BASE%\ReadyContent\prompts\*"
del /s /q "%BASE%\ReadyContent\photosCompress\*"
del /s /q "%BASE%\ReadyContent\readyPosts\*"
del /s /q "%BASE%\ReadyContent\shorts\*"
mkdir "%BASE%\ReadyContent
mkdir "%BASE%\ReadyContent\readyArticles"
mkdir "%BASE%\ReadyContent\readyDescriptions"
mkdir "%BASE%\ReadyContent\prompts"
mkdir "%BASE%\ReadyContent\photosCompress"
mkdir "%BASE%\ReadyContent\readyPosts"
mkdir "%BASE%\ReadyContent\shorts"

cd "%BASE%/App/ArticleGenerator"
echo(
echo content_generator.py
echo(
python content_generator.py
cd "%BASE%/App/ShortsGenerator"
echo(
echo backup_and_clean.py
echo(
python backup_and_clean.py
echo(
echo shorts_gen.py
echo(
python shorts_gen.py
echo(
echo merge_to_mp4.py
echo(
python merge_to_mp4.py
echo(
echo merge_videos.py
echo(
python merge_videos.py
echo(
echo speed_up_videos.py
echo(
python speed_up_videos.py
echo(
cd "%BASE%\App\Upload"
python autoUpload.py
cd "%BASE%\App\AutomatedCommunityManagement"
python comment_responder.py
pause