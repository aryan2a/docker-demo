# docker-demo

![Test and Deploy](https://github.com/aryan2a/docker-demo/actions/workflows/deploy.yml/badge.svg)

A small FastAPI service, packaged with Docker and deployed to AWS EC2 through a GitHub Actions CI/CD pipeline.

The app is deliberately tiny. The point of this repo is the pipeline around it: every `git push` to `main` is tested automatically, and only if the tests pass is the new version deployed to the server. No manual steps on the server.

## How it works

```
git push
   │
   ▼
GitHub Actions
   │
   ├── test job    install dependencies → run pytest
   │                  │
   │                  │ passes?  (if not, the deploy job is skipped)
   │                  ▼
   └── deploy job  SSH into EC2 → git pull → docker build → restart container
                                                   │
                                                   ▼
                                    http://<EC2_PUBLIC_IP>:8000
```

## Tech stack

| Layer | Tool |
|---|---|
| App | Python 3.11, FastAPI, Uvicorn |
| Packaging | Docker |
| Tests | pytest, FastAPI `TestClient` (uses httpx) |
| CI/CD | GitHub Actions: `actions/checkout`, `actions/setup-python`, `appleboy/ssh-action` |
| Hosting | AWS EC2 (Ubuntu 24.04, t3.micro) |

## Project structure

```
docker-demo/
├── .github/workflows/deploy.yml   # CI/CD pipeline: test, then deploy
├── app.py                         # FastAPI app with one endpoint: GET /
├── test_app.py                    # pytest test for that endpoint
├── Dockerfile                     # recipe for the container image
├── requirements.txt               # runtime dependencies
├── requirements-dev.txt           # runtime + test dependencies
└── .dockerignore                  # files kept out of the image
```

## Run locally

**With Docker**

```bash
docker build -t hello-api .
docker run --rm -p 8000:8000 hello-api
```

Open <http://localhost:8000> for the JSON message and <http://localhost:8000/docs> for FastAPI's auto-generated docs. `--rm` deletes the container when it stops.

**Without Docker**

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

**Run the tests**

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Deploy your own copy

One-time setup on AWS and GitHub. After this, deployments are automatic.

1. **Launch an EC2 instance.** Ubuntu Server 24.04, a free-tier-eligible instance type, and a new key pair (`.pem` file).
2. **Security group inbound rules.** SSH (port 22) and Custom TCP port 8000. The GitHub runner connects from changing addresses, so SSH has to be open to `0.0.0.0/0`. See the limitations below.
3. **Install Docker on the server.**
   ```bash
   sudo apt update
   sudo apt install -y docker.io
   sudo usermod -aG docker ubuntu
   ```
   Log out and back in so the group change applies.
4. **Clone the repo and start the container once.**
   ```bash
   git clone https://github.com/<your-username>/docker-demo.git ~/docker-demo
   cd ~/docker-demo
   docker build -t hello-api .
   docker run -d --name myapi --restart unless-stopped -p 8000:8000 hello-api
   ```
5. **Add three repository secrets** under *Settings → Secrets and variables → Actions*:

   | Secret | Value |
   |---|---|
   | `EC2_HOST` | The server's public IPv4 address |
   | `EC2_USER` | `ubuntu` |
   | `EC2_SSH_KEY` | Full contents of the `.pem` file, including the BEGIN/END lines |

6. **Push to `main`.** Open the *Actions* tab to watch the run.

## The pipeline in detail

The workflow lives in `.github/workflows/deploy.yml` and runs on every push to `main`.

**`test` job** runs on a temporary GitHub-hosted Ubuntu machine:
1. `actions/checkout` downloads the repo onto it.
2. `actions/setup-python` installs Python 3.11, matching the Dockerfile.
3. `pip install -r requirements-dev.txt` installs the app and test tools.
4. `python -m pytest` runs the tests. Any failure fails the job.

**`deploy` job** has `needs: test`, so it starts only after the test job passes. It logs into the server over SSH and runs:

```bash
set -e                      # stop at the first error
cd ~/docker-demo
git pull origin main        # fetch the new code
docker build -t hello-api . # build a new image
docker stop myapi || true   # "|| true" ignores the error if nothing is running
docker rm myapi || true
docker run -d --name myapi --restart unless-stopped -p 8000:8000 hello-api
docker image prune -f       # delete old nameless images
```

**Checking that the guard works.** Change an assertion in `test_app.py` so it fails, then push. The `test` job turns red, the `deploy` job is skipped, and the running app is unchanged.

## Concepts at a glance

| Term | Plain-English meaning |
|---|---|
| Image | The packed, unchanging recipe for the app (`docker build`) |
| Container | A running copy cooked from an image (`docker run`) |
| Runner | The temporary computer GitHub lends to run a job |
| Secret | An encrypted value stored in the repo, readable only by workflows |
| CI / CD | Continuous Integration (test automatically) / Continuous Deployment (ship automatically) |

## Known limitations

- **SSH is open to the internet.** Login still requires the private key, since password login is off on Ubuntu EC2 images. Acceptable for a learning project, but it should be tightened for anything real.
- **The public IP changes** when the instance is stopped and started. Update the `EC2_HOST` secret afterwards, or attach an Elastic IP.
- **HTTP only.** There is no domain or HTTPS.
- **The server builds the image.** A registry-based flow would be faster and more reproducible.
- **Every push to `main` triggers a deploy,** including edits that only touch documentation.

## Roadmap

- [ ] Build the image in CI and push it to a registry (Docker Hub or AWS ECR); the server only pulls it
- [ ] Docker Compose for running several services together
- [ ] Domain name and HTTPS
- [ ] A RAG endpoint with an automated evaluation suite that gates every release

## Author

Built by Aryan Arora ([@aryan2a](https://github.com/aryan2a)) as a hands-on project to learn Git, Docker, AWS EC2 and CI/CD.
