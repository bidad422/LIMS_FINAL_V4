import pathlib

form_path = pathlib.Path(r"D:\LIMS_FINAL_V3\templates\uncertainty\form.html")
content = form_path.read_text(encoding='utf-8')

# ۱. تعریف بلوک جدید HTML برای ۳ تب اسپکترو
new_spectro_block = '''  <div class="fcard">
    <div class="fhead">⚗️ قرائت‌های عناصر (حداقل ۲ قرائت برای هر عنصر در هر سری)</div>
    <div class="fbody">
      <!-- تب‌ها -->
      <ul class="nav nav-tabs mb-3" id="spectroTabs" role="tablist" style="direction: rtl; border-bottom: 2px solid #e2e8f0;">
        <li class="nav-item" role="presentation">
          <button class="nav-link active" id="series1-tab" data-bs-toggle="tab" data-bs-target="#series1" type="button" role="tab" aria-controls="series1" aria-selected="true" style="font-weight: bold; color: #1e3a8a;">
            🔬 سری ۱ (اپراتور/روز اول)
          </button>
        </li>
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="series2-tab" data-bs-toggle="tab" data-bs-target="#series2" type="button" role="tab" aria-controls="series2" aria-selected="false" style="font-weight: bold; color: #1e3a8a;">
            🔬 سری ۲ (اپراتور/روز دوم) <span class="badge bg-secondary" style="font-size: 0.7em; vertical-align: middle;">اختیاری</span>
          </button>
        </li>
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="series3-tab" data-bs-toggle="tab" data-bs-target="#series3" type="button" role="tab" aria-controls="series3" aria-selected="false" style="font-weight: bold; color: #1e3a8a;">
            🔬 سری ۳ (اپراتور/روز سوم) <span class="badge bg-secondary" style="font-size: 0.7em; vertical-align: middle;">اختیاری</span>
          </button>
        </li>
      </ul>

      <!-- محتوای تب‌ها -->
      <div class="tab-content" id="spectroTabsContent">
        {% for series_num in "123" %}
        <div class="tab-pane fade {% if series_num == '1' %}show active{% endif %}" id="series{{ series_num }}" role="tabpanel" aria-labelledby="series{{ series_num }}-tab">
          {% if series_num != '1' %}
            <div class="alert alert-warning py-2 mb-2" style="font-size: 0.85rem; border-radius: 6px;">
              <i class="bi bi-exclamation-triangle"></i>
              <strong>توجه:</strong> برای محاسبه <strong>تجدیدپذیری (u_reprod)</strong> با ANOVA، این سری باید توسط اپراتور دیگر یا در روز دیگر با آماده‌سازی مجدد ثبت شود.
            </div>
          {% endif %}
          <div style="overflow-x:auto;">
            <table class="spec-table" style="width:100%; border-collapse:collapse; direction:ltr;">
              <thead>
                <tr>
                  <th style="background:#f8fafc; padding:8px; font-size:0.75rem;">#</th>
                  {% for e in spectro_elements %}<th style="background:#f8fafc; padding:8px; font-size:0.75rem;">{{ e }}</th>{% endfor %}
                </tr>
              </thead>
              <tbody>
                {% for i in spectro_rows_range %}
                <tr>
                  <td style="color:#94a3b8; font-weight:700; text-align:center; padding:4px;">{{ i }}</td>
                  {% for e in spectro_elements %}
                  <td style="padding:3px;">
                    <input type="text" inputmode="decimal" 
                           name="series_{{ series_num }}_el{{ e }}_{{ forloop.counter0 }}" 
                           class="spectro-input"
                           data-series="{{ series_num }}" data-elem="{{ e }}" data-idx="{{ forloop.counter0 }}"
                           style="width:72px; padding:4px 6px; font-size:0.78rem; border:1.5px solid #cbd5e1; border-radius:5px; text-align:center;">
                  </td>
                  {% endfor %}
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
        {% endfor %}
      </div>
    </div>
  </div>'''

# ۲. پیدا کردن و جایگزینی بلوک قدیمی جدول اسپکترو
old_pattern_start = '  <div class="fcard">\n    <div class="fhead">⚗️ قرائت‌های عناصر'
old_pattern_end = '    </div>\n  </div>\n\n  {% else %}'

start_idx = content.find(old_pattern_start)
if start_idx != -1:
    end_idx = content.find(old_pattern_end, start_idx)
    if end_idx != -1:
        # جایگزینی
        content = content[:start_idx] + new_spectro_block + '\n\n  {% else %}' + content[end_idx + len('    </div>\n  </div>\n\n  {% else %}'):]
        print("✅ بلوک جدول اسپکترو با موفقیت به ۳ تب تبدیل شد.")
    else:
        print("❌ پایان بلوک قدیمی پیدا نشد.")
else:
    print("❌ شروع بلوک قدیمی پیدا نشد. ممکن است قبلاً اصلاح شده باشد.")

# ۳. به‌روزرسانی جاوااسکریپت برای پشتیبانی از ۳ سری
old_js = '''  // فیلدهای اسپکترو
  if (prevInputs.elements) {
    Object.keys(prevInputs.elements).forEach(function (e) {
      var vals = prevInputs.elements[e];
      vals.forEach(function (v, i) {
        var el = document.querySelector('[name="el_' + e + '_' + i + '"]');
        if (el) el.value = v;
      });
    });
  }'''

new_js = '''  // فیلدهای اسپکترو (پشتیبانی از ۳ سری)
  if (prevInputs.elements || prevInputs.element_series) {
    var seriesData = prevInputs.element_series || {};
    // اگر element_series نبود، از elements به عنوان سری ۱ استفاده کن
    if (Object.keys(seriesData).length === 0 && prevInputs.elements) {
      Object.keys(prevInputs.elements).forEach(function(e) {
        seriesData[e] = [prevInputs.elements[e]];
      });
    }
    
    Object.keys(seriesData).forEach(function(e) {
      var seriesList = seriesData[e];
      seriesList.forEach(function(vals, sIdx) {
        var seriesNum = sIdx + 1;
        if (seriesNum > 3) return; // فقط تا ۳ سری
        vals.forEach(function(v, i) {
          if (i >= 10) return; // حداکثر ۱۰ ردیف
          var selector = 'input[data-series="' + seriesNum + '"][data-elem="' + e + '"][data-idx="' + i + '"]';
          var el = document.querySelector(selector);
          if (el) el.value = v;
        });
      });
    });
  }'''

if old_js in content:
    content = content.replace(old_js, new_js)
    print("✅ جاوااسکریپت پرکردن خودکار برای ۳ سری به‌روزرسانی شد.")
else:
    print("⚠️ الگوی جاوااسکریپت قدیمی پیدا نشد (ممکن است قبلاً تغییر کرده باشد).")

# ۴. ذخیره فایل
form_path.write_text(content, encoding='utf-8')
print("🎉 فایل form.html با موفقیت ذخیره شد!")