# Uploading Acadeloop to GitHub

This folder is the repository root.

## GitHub web
1. Create a new empty repository.
2. Extract this ZIP on your computer.
3. Open the extracted `Acadeloop_GitHub_Repository_v1_0_1` folder.
4. Upload the **contents of the folder**, not the ZIP itself.
5. Commit the files to `main`.

## Git command line
```bash
git init
git add .
git commit -m "Initial Acadeloop v1.0.1"
git branch -M main
git remote add origin <YOUR-REPOSITORY-URL>
git push -u origin main
```

Do not commit private credentials, API keys, passwords, or production user data.
