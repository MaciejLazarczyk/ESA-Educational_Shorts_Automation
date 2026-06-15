@echo on
set "BASE=%~dp0..\.."
mkdir "%BASE%\ReadyContent
mkdir "%BASE%\ReadyContent\readyArticles"
mkdir "%BASE%\ReadyContent\readyDescriptions"
mkdir "%BASE%\ReadyContent\prompts"
mkdir "%BASE%\ReadyContent\photosCompress"
mkdir "%BASE%\ReadyContent\readyPosts"

cd "%BASE%/App/ArticleGenerator"
python content_generator.py
pause