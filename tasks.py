from invoke import run, task

NAME = 'pylnk3'


@task
def build(c):
    run('python setup.py sdist bdist_wheel')


@task
def clean(c):
    run('rm -rf ./build ./dist ./*.egg-info')


@task
def upload_test(c):
    run('python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*')


@task
def upload_release(c):
    run('python -m twine upload dist/*')


@task
def install_test(c):
    run(f'python -m pip install --index-url https://test.pypi.org/simple/ --no-deps --pre -U {NAME}')


@task
def install_release(c):
    run(f'python -m pip install -U {NAME}')


@task
def uninstall(c):
    run(f'python -m pip uninstall {NAME}')
