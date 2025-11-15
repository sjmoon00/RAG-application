# My Python Project

이 프로젝트는 uv를 사용하여 Python 환경을 관리합니다. uv는 빠르고 효율적인 Python 패키지 관리 도구로, venv와 pip의 대안입니다.

## 전제 조건
- Python 3.11 이상 설치됨.
- uv 설치: 아직 설치되지 않았다면 [uv 공식 문서](https://docs.astral.sh/uv/getting-started/installation/)를 참조하세요. 간단히 설치하려면 (macOS/Linux 기준):
 
### 윈도우
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
### mac
```bash
bashbrew install uv
```

## 프로젝트 사용 방법

### 1. GitHub 리포지토리 클론:
```bash
git clone https://github.com/yourusername/my-project.git
cd my-project
```

### 2. 의존성 설치 및 환경 동기화:
- pyproject.toml과 uv.lock 파일을 기반으로 자동으로 가상 환경을 생성하고 패키지를 설치합니다.

```bash
uv sync
```

### 3. 노트북 실행