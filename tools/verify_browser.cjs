/* Optional UI verification. Run after installing Playwright and Chromium.
 * Uses only local demo data. Creates and then deletes one test student.
 */
const { chromium } = require('playwright');
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.TEST_BROWSER_EXECUTABLE ? { executablePath: process.env.TEST_BROWSER_EXECUTABLE } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1040 }, deviceScaleFactor: 1, reducedMotion: 'reduce' });
  const page = await context.newPage();
  const base = process.env.TEST_BASE_URL || 'http://127.0.0.1:8000';
  const screenshots = path.resolve(__dirname, '..', 'screenshots');
  fs.mkdirSync(screenshots, { recursive: true });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
  await page.goto(base);
  assert.ok(page.url().includes('/login/'));
  await page.getByLabel('Username').fill('admin');
  await page.getByLabel('Password', { exact: true }).fill('Admin@12345');
  await Promise.all([page.waitForURL(base + '/'), page.getByRole('button', { name: 'Sign in' }).click()]);
  await page.waitForFunction(() => typeof Chart !== 'undefined' && Object.keys(Chart.instances).length === 4);
  await page.screenshot({ path: path.join(screenshots, 'dashboard.png'), fullPage: true, animations: 'disabled' });
  const modules = ['students', 'teachers', 'departments', 'courses', 'subjects', 'classes', 'enrollments', 'attendance', 'results', 'accounts'];
  const detailLinks = [];
  for (const module of modules) {
    await page.goto(`${base}/${module}/`);
    assert.ok(await page.locator('h1').isVisible());
    const link = await page.locator('tbody a.person-cell').first().getAttribute('href');
    if (link) detailLinks.push(link);
    if (['students', 'attendance', 'results'].includes(module)) {
      await page.screenshot({ path: path.join(screenshots, `${module}.png`), fullPage: true, animations: 'disabled' });
    }
    await page.goto(`${base}/${module}/add/`);
    assert.ok(await page.locator('form.record-form').isVisible());
  }
  for (const link of detailLinks) {
    await page.goto(base + link);
    assert.ok(await page.locator('.detail-panel').isVisible());
    await page.goto(base + link + 'edit/');
    assert.ok(await page.locator('form.record-form').isVisible());
    await page.goto(base + link + 'delete/');
    assert.ok(await page.getByRole('button', { name: /Yes, delete/ }).isVisible());
  }
  await page.goto(base + '/students/add/');
  await page.screenshot({ path: path.join(screenshots, 'student_form.png'), fullPage: true, animations: 'disabled' });
  const id = `UI-${Date.now().toString().slice(-10)}`;
  await page.getByLabel('Student id', { exact: false }).fill(id);
  await page.getByLabel('First name', { exact: false }).fill('Browser');
  await page.getByLabel('Last name', { exact: false }).fill('Verification');
  await page.getByLabel('Email', { exact: false }).fill(`${id.toLowerCase()}@example.com`);
  await page.getByLabel('Gender', { exact: false }).selectOption('other');
  await page.getByLabel('Date of birth', { exact: false }).fill('2004-01-10');
  const course = await page.locator('#id_course option').evaluateAll(options => options.find(option => option.textContent === 'BS Computer Science')?.value);
  const department = await page.locator('#id_department option').evaluateAll(options => options.find(option => option.textContent === 'Computer Science')?.value);
  await page.locator('#id_department').selectOption(department);
  await page.locator('#id_course').selectOption(course);
  await page.locator('#id_semester').fill('1');
  await Promise.all([page.waitForURL(base + '/students/'), page.getByRole('button', { name: 'Create student' }).click()]);
  await page.goto(base + '/students/?q=' + id);
  await page.locator('tbody a.person-cell').first().click();
  await page.getByRole('link', { name: 'Edit student' }).click();
  await page.getByLabel('Last name', { exact: false }).fill('Verified');
  await Promise.all([page.waitForURL(base + '/students/'), page.getByRole('button', { name: 'Save changes' }).click()]);
  await page.goto(base + '/students/?q=' + id);
  await page.locator('tbody a.person-cell').first().click();
  await page.getByRole('link', { name: 'Delete this student' }).click();
  await Promise.all([page.waitForURL(base + '/students/'), page.getByRole('button', { name: 'Yes, delete student' }).click()]);
  await page.goto(base + '/attendance/register/');
  const subject = await page.locator('#id_subject option').nth(1).getAttribute('value');
  await page.locator('#id_subject').selectOption(subject);
  await page.getByRole('button', { name: /Load student roster/ }).click();
  assert.ok(await page.getByRole('button', { name: 'Save attendance' }).isVisible());
  assert.ok(await page.locator('input[type=radio][value=present]').count() > 0);
  await page.goto(base + '/admin/');
  assert.ok(await page.getByRole('heading', { name: 'Institution administration' }).isVisible());
  await page.screenshot({ path: path.join(screenshots, 'admin_panel.png'), fullPage: true, animations: 'disabled' });
  for (const module of ['students/student', 'teachers/teacher', 'academics/department', 'academics/course', 'academics/subject', 'academics/classgroup', 'academics/enrollment', 'attendance/attendance', 'results/result']) {
    await page.goto(`${base}/admin/${module}/`);
    assert.ok(await page.locator('#changelist').isVisible());
  }
  await page.setViewportSize({ width: 390, height: 844 });
  for (const url of ['/', '/students/', '/students/add/', '/attendance/', '/results/']) {
    await page.goto(base + url);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  }
  await page.goto(base + '/');
  await page.getByRole('button', { name: 'Open navigation' }).click();
  assert.equal(await page.locator('#menu-toggle').getAttribute('aria-expanded'), 'true');
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#menu-toggle').getAttribute('aria-expanded'), 'false');
  await page.screenshot({ path: path.join(screenshots, 'mobile_dashboard.png'), fullPage: true, animations: 'disabled' });
  assert.deepEqual(errors, [], 'No failed responses or JavaScript errors');
  console.log('PASS: demo login, four charts, all modules/forms/details, student CRUD, attendance roster, admin models, mobile layout, and six README screenshots.');
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });
