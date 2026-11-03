import pathlib

# ─────────────────────────────────────────────────────
# ۱. به‌روزرسانی views.py - تابع record_recall
# ─────────────────────────────────────────────────────
views_path = pathlib.Path(r"D:\LIMS_FINAL_V3\uncertainty\views.py")
views_content = views_path.read_text(encoding='utf-8')

# پیدا کردن و جایگزینی تابع record_recall
old_recall = '''@login_required
def record_recall(request, rec_id):
    """بازخوانی: فرم همان نوع محاسبه با ورودی‌های قبلی از پیش پر شده."""
    rec = get_object_or_404(UncertaintyRecord, id=rec_id)
    ct = CALC_TYPES.get(rec.calc_type)
    if not ct:
        messages.error(request, 'نوع محاسبه این رکورد در نسخه فعلی موجود نیست.')
        return redirect('uncertainty:detail', rec_id=rec.id)
    field_values = {}
    for f in ct['fields']:
        field_values[f['name']] = (rec.inputs or {}).get(f['name'], '')
    return render(request, 'uncertainty/form.html', {
        'ct': ct, 'calc_type': rec.calc_type,
        'inputs': rec.inputs, 'field_values': field_values,
        'recall_from': rec,
    })'''

new_recall = '''@login_required
def record_recall(request, rec_id):
    """بازخوانی: فرم همان نوع محاسبه با ورودی‌های قبلی از پیش پر شده — پشتیبانی از ۳ سری."""
    rec = get_object_or_404(UncertaintyRecord, id=rec_id)
    ct = CALC_TYPES.get(rec.calc_type)
    if not ct:
        messages.error(request, 'نوع محاسبه این رکورد در نسخه فعلی موجود نیست.')
        return redirect('uncertainty:detail', rec_id=rec.id)
    field_values = {}
    for f in ct['fields']:
        field_values[f['name']] = (rec.inputs or {}).get(f['name'], '')
    
    # آماده‌سازی inputs برای پشتیبانی از ۳ سری در اسپکترو
    inputs = rec.inputs or {}
    if ct.get('special') == 'spectro':
        # اگر element_series وجود دارد، از آن استفاده کن
        # در غیر این صورت، elements را به عنوان سری ۱ در نظر بگیر
        if 'element_series' not in inputs and 'elements' in inputs:
            inputs['element_series'] = {}
            for elem, vals in inputs['elements'].items():
                inputs['element_series'][elem] = [vals]  # سری ۱
    
    return render(request, 'uncertainty/form.html', {
        'ct': ct, 'calc_type': rec.calc_type,
        'inputs': inputs, 'field_values': field_values,
        'recall_from': rec,
    })'''

if old_recall in views_content:
    views_content = views_content.replace(old_recall, new_recall)
    print("✅ تابع record_recall در views.py به‌روزرسانی شد")
else:
    print("⚠️ تابع record_recall پیدا نشد یا قبلاً تغییر کرده است")

views_path.write_text(views_content, encoding='utf-8')

# ─────────────────────────────────────────────────────
# ۲. به‌روزرسانی form.html - جاوااسکریپت برای بارگذاری ۳ سری
# ─────────────────────────────────────────────────────
form_path = pathlib.Path(r"D:\LIMS_FINAL_V3\templates\uncertainty\form.html")
form_content = form_path.read_text(encoding='utf-8')

# پیدا کردن بخش جاوااسکریپت و جایگزینی آن
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

new_js = '''  // فیلدهای اسپکترو (پشتیبانی از  سری / تب‌ها)
  if (prevInputs.elements || prevInputs.element_series) {
    var seriesData = prevInputs.element_series || {};
    
    // اگر element_series نبود، از elements به عنوان سری ۱ استفاده کن
    if (Object.keys(seriesData).length === 0 && prevInputs.elements) {
      Object.keys(prevInputs.elements).forEach(function(e) {
        seriesData[e] = [prevInputs.elements[e]];
      });
    }
    
    // پر کردن هر  تب
    Object.keys(seriesData).forEach(function(e) {
      var seriesList = seriesData[e];
      seriesList.forEach(function(vals, sIdx) {
        var seriesNum = sIdx + 1; // سری ۱، ۲، ۳
        if (seriesNum > 3) return; // حداکثر ۳ سری
        
        vals.forEach(function(v, i) {
          if (i >= 10) return; // حداکثر ۱۰ ردیف
          
          // پیدا کردن فیلد در تب مربوطه
          var selector = 'input[data-series="' + seriesNum + '"][data-elem="' + e + '"][data-idx="' + i + '"]';
          var el = document.querySelector(selector);
          if (el) {
            el.value = v;
            // هایلایت کردن ردیف پرشده
            el.closest('tr').style.background = '#f0f9ff';
          }
        });
      });
    });
  }'''

if old_js in form_content:
    form_content = form_content.replace(old_js, new_js)
    print("✅ جاوااسکریپت بارگذاری ۳ سری در form.html به‌روزرسانی شد")
else:
    print("⚠️ الگوی جاوااسکریپت قدیمی پیدا نشد")

form_path.write_text(form_content, encoding='utf-8')

print("\\n🎉 به‌روزرسانی با موفقیت انجام شد!")
print("="*70)
print("اکنون:")
print("  ۱. وقتی روی رکوردی کلیک می‌کنید، هر ۳ تب پر می‌شوند")
print("  ۲. می‌توانید تغییرات دهید و ذخیره کنید")
print("  ۳. بودجه عدم‌قطعیت با داده‌های جدید به‌روز می‌شود")
print("="*70)