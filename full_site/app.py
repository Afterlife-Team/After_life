"""404 Afterlife — multi-page website preservation & redesign backend UI."""
import json
import os
import streamlit as st
import streamlit.components.v1 as components

from services.site_bundle import site_from_zip, to_zip, WebsiteError
from services.encoding import decode_html
from services.analysis import analyze_site
from services.preview import preview_page
from services.redesign import modernize_site
from services.ai_bridge import request_ai_redesign, apply_ai_changes, AIIntegrationError
from services.archive_site import find_snapshot, recover_archived_site, ArchiveError
from services.security import UnsafeURL

st.set_page_config(page_title='404 Afterlife | Real Website Modernization', page_icon='🕸️', layout='wide')
st.title('🕸️ 404 AFTERLIFE')
st.caption('Dead websites, reborn • Keep the real pages, content and assets')
st.write('Upload a complete old website ZIP, or recover an available Wayback snapshot. Compare **the same page** before and after, then download the entire website.')

if 'result' not in st.session_state:
    st.session_state.result = None

source_choice = st.radio('Choose Website Source', ['Upload ZIP', 'Recover from URL'], horizontal=True)
url = None
chosen_year = None
zip_file = None
if source_choice == 'Upload ZIP':
    zip_file = st.file_uploader('Upload the original website (.zip)', type=['zip'],
                                help='Include all your HTML, CSS, images and other static files. Max 15 MB compressed.')
else:
    url = st.text_input('Original URL', placeholder='https://example.com/')
    archive_year_mode = st.radio('Archive year', ['Automatic (closest)', 'Choose Year'],horizontal=True)
    if archive_year_mode == 'Choose Year':
        chosen_year = st.selectbox('Choose archive year', list(range(2026,1995,-1)), index=16)

st.markdown('#### Redesign method')
method = st.radio('Choose a way to redesign',
                  ['Safe CSS refresh (works now)', 'Team AI endpoint', 'Import team AI JSON'],
                  horizontal=True,
                  help='CSS refresh is deterministic, NOT AI. The other options use Rana/Suzy integration.')
manual_ai_file = None
if method == 'Team AI endpoint':
    if os.environ.get('AFTERLIFE_AI_ENDPOINT'):
        st.info('AI endpoint configured by environment variable.')
    else:
        st.warning('AI endpoint not set. Configure AFTERLIFE_AI_ENDPOINT before running the app.')
elif method == 'Import team AI JSON':
    manual_ai_file = st.file_uploader('AI result JSON',type=['json'],
                                      help='Expected: {"files": {"index.html": "<html>...</html>", ...}}')

if st.button('♻️ Revive Entire Website', type='primary'):
    st.session_state.result = None
    try:
        with st.spinner('Reading and validating original website...'):
            if source_choice == 'Upload ZIP':
                if zip_file is None:
                    st.error('Upload a ZIP file first.');st.stop()
                original = site_from_zip(zip_file.getvalue())
            else:
                if not url:
                    st.error('Enter the original URL first.');st.stop()
                snapshot = find_snapshot(url, chosen_year)
                if snapshot is None:
                    st.error('No archived snapshot found for that URL / year.');st.stop()
                snapshot['requested_year'] = chosen_year
                original = recover_archived_site(snapshot)
            report_before = analyze_site(original)
        with st.spinner('Applying the selected redesign to all pages...'):
            if method == 'Safe CSS refresh (works now)':
                revised = modernize_site(original)
                method_label = 'CSS refresh — NOT AI'
            elif method == 'Team AI endpoint':
                revised = request_ai_redesign(original)
                method_label = 'Team AI endpoint'
            else:
                if manual_ai_file is None:
                    st.error('Upload the team AI JSON response first.');st.stop()
                try:
                    imported = json.loads(manual_ai_file.getvalue().decode('utf-8-sig'))
                except (ValueError, UnicodeError) as exc:
                    raise AIIntegrationError('Invalid JSON file.') from exc
                if not isinstance(imported,dict) or not isinstance(imported.get('files'),dict):
                    raise AIIntegrationError('JSON must be an object with a "files" dictionary.')
                revised = apply_ai_changes(original, imported['files'])
                method_label = 'Imported file edits (AI provenance not verified)'
            report_after = analyze_site(revised)
        st.session_state.result = {
            'original': original, 'revised': revised,
            'before_report': report_before, 'after_report': report_after,
            'method': method_label,
        }
        st.success(f'Website processed: {len(original.pages)} HTML page(s), {len(revised.files)} output file(s).')
    except (WebsiteError, UnsafeURL, ArchiveError, AIIntegrationError, ValueError) as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f'Unexpected error: {type(exc).__name__}: {exc}')
        st.exception(exc)

result = st.session_state.result
if result:
    original, revised = result['original'],result['revised']
    report = result['before_report']; after_report=result['after_report']
    st.divider()
    st.subheader('📁 Real website files')
    changed_pages = sum(original.files[p] != revised.files[p] for p in original.pages)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric('HTML pages',len(original.pages))
    c2.metric('Updated HTML pages',f'{changed_pages}/{len(original.pages)}')
    c3.metric('Output files',len(revised.files))
    c4.metric('Missing assets/links (After)',len(after_report['missing_references']))
    st.caption(f"Source: {original.source.upper()}  •  Homepage: {original.homepage}  •  Redesign: {result['method']}")
    if original.source == 'wayback' and original.recovery:
        rec = original.recovery
        capture = rec['capture']
        st.subheader('🕰️ Archive date & recovery coverage')
        st.write(f"**Selected Wayback capture:** {capture['date_utc']}")
        selected = capture.get('requested_year')
        st.caption('Archive selection: ' + (f'Requested year {selected}' if selected is not None else 'Automatic (closest available capture)'))
        st.caption(capture['provenance_note'])
        pages = rec['pages']
        assets = rec['assets']
        p1, p2, p3, p4 = st.columns(4)
        p1.metric('Page URLs discovered', pages['discovered'])
        p2.metric('Pages recovered', pages['recovered'])
        p3.metric('Pages failed', pages['failed'])
        p4.metric('Pages not attempted', pages['not_attempted'])
        a1, a2, a3, a4 = st.columns(4)
        a1.metric('Asset URLs discovered', assets['discovered'])
        a2.metric('Assets recovered', assets['recovered'])
        a3.metric('Assets failed', assets['failed'])
        a4.metric('Assets not attempted', assets['not_attempted'])
        st.caption(f"Image URLs recovered: {assets['image_urls_recovered']}/{assets['image_urls_discovered']} discovered on-host; off-host assets not downloaded: {assets['external_not_downloaded']}.")
        st.info(rec['coverage_note'])
        with st.expander('📋 Recovery details — missing pages/assets & reasons'):
            st.json(rec)
        st.download_button('⬇️ Download Wayback recovery report (JSON)',
                           data=json.dumps(rec, ensure_ascii=False, indent=2),
                           file_name='404_afterlife_recovery_report.json', mime='application/json')
    elif original.source == 'zip':
        st.caption('ZIP input: only the files included in the uploaded ZIP can be validated; complete original-site coverage cannot be inferred.')
    for warning in original.warnings:
        st.warning(warning)
    if report['missing_references']:
        with st.expander('⚠️ Missing references in the original website'):
            st.code('\n'.join(report['missing_references']))
    if after_report['missing_references']:
        with st.expander('⚠️ Missing references in redesigned website'):
            st.code('\n'.join(after_report['missing_references']))
    with st.expander('🔍 Full-site analysis (all pages)'):
        st.json(report)
    st.divider()
    st.subheader('🌐 Before / After — Same Original Page')
    chosen_page = st.selectbox('Choose which original page to compare',original.pages,
                                index=original.pages.index(original.homepage))
    before_col, after_col = st.columns(2, gap='medium')
    with before_col:
        st.markdown('**🕰️ BEFORE — original website**')
        components.html(preview_page(original,chosen_page),height=580,scrolling=True)
    with after_col:
        st.markdown('**✨ AFTER — updated original website**')
        components.html(preview_page(revised,chosen_page),height=580,scrolling=True)
    st.caption('Static previews: scripts are disabled, forms cannot submit, external resources are blocked. Use the page selector for navigation. SVG images are sanitized.')
    st.divider()
    st.subheader('📦 Download the complete real website')
    left,right = st.columns(2)
    with left:
        st.download_button('⬇️ Download redesigned website ZIP', data=to_zip(revised),
                           file_name='404_afterlife_redesigned_site.zip',mime='application/zip',
                           use_container_width=True)
    with right:
        st.download_button('⬇️ Download original website ZIP', data=to_zip(original),
                           file_name='404_afterlife_original_site.zip',mime='application/zip',
                           use_container_width=True)
    # Contract export: HTML/CSS are text only; binary images stay in original bundle.
    payload_files = {p: decode_html(v) for p,v in original.files.items()
                     if p.lower().endswith(('.html','.htm','.css'))}
    request = {
        'task':'modernize_existing_website',
        'homepage':original.homepage,
        'files':payload_files,
        'assets':sorted(p for p in original.files if p not in payload_files),
        'instructions':'Return {"files": {"existing_file_path": "updated HTML or CSS"}}. Preserve all content, links, and asset paths.'
    }
    st.download_button('🧠 Export input JSON for AI team',data=json.dumps(request,ensure_ascii=False,indent=2),
                       file_name='404_afterlife_team_ai_input.json',mime='application/json')
    st.caption('The output ZIP retains original JavaScript files (if present). Review them before deploying. The CSS refresh is a non-AI baseline; do not present it as AI-generated.')

st.divider()
st.caption('Hackathon prototype • Only upload websites you have permission to modify • Archive recovery can be incomplete.')
