from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

setup(
	name="ai_test_suite",
	version="0.0.1",
	description="AI-powered testing application for Frappe/ERPNext",
	author="Nalam Hospital",
	author_email="md.office@nalamhospital.in",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
)
