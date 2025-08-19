name: Issue to Static Post (Gemini)

on:
  issues:
    types: [opened, edited, reopened, labeled]

permissions:
  contents: write
  issues: write

jobs:
  gen:
    # Titre contient [AI-POST] OU label 'publish'
    if: contains(github.event.issue.title, '[AI-POST]') || contains(github.event.issue.labels.*.name, 'publish')
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo (main)
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      # On garde les scripts hors du YAML pour éviter les erreurs d'indentation/quotes
      - name: Stage scripts
        run: |
          mkdir -p /tmp/gen
          cp -v scripts/issue_to_static.py /tmp/gen/issue_to_static.py
          cp -v scripts/bootstrap.sh       /tmp/gen/bootstrap.sh
          chmod +x /tmp/gen/bootstrap.sh

      - name: Switch to gh-pages
        run: |
          git fetch origin gh-pages || true
          if git ls-remote --exit-code origin gh-pages >/dev/null 2>&1; then
            git checkout gh-pages
            git pull origin gh-pages
          else
            git checkout --orphan gh-pages
            rm -rf *
          fi

      - name: Bootstrap static site (if missing)
        run: /tmp/gen/bootstrap.sh

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install deps
        run: pip install requests markdown

      - name: Generate post with Gemini
        id: gen
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          ISSUE_TITLE: ${{ github.event.issue.title }}
          ISSUE_BODY:  ${{ github.event.issue.body }}
          HINT_TAGS:   ""
        run: |
          python /tmp/gen/issue_to_static.py > /tmp/slug.txt
          echo "slug=$(cat /tmp/slug.txt)" >> $GITHUB_OUTPUT

      - name: Commit & push to gh-pages
        run: |
          git config user.name  "github-actions"
          git config user.email "actions@users.noreply.github.com"
          git add index.html assets/style.css posts.json posts .nojekyll
          git commit -m "post: ${{ steps.gen.outputs.slug }} (#${{ github.event.issue.number }})" || echo "Nothing to commit"
          git push origin gh-pages

      - name: Comment with link
        uses: actions-ecosystem/action-create-comment@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          number: ${{ github.event.issue.number }}
          body: |
            ✅ Publié : https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}/posts/${{ steps.gen.outputs.slug }}.html
