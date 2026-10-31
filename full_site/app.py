"""404 Afterlife — multi-page website preservation & redesign backend UI."""
import json
import hashlib
from datetime import date
import streamlit as st
import streamlit.components.v1 as components

from services.site_bundle import site_from_zip, to_zip, WebsiteError
from services.analysis import analyze_site
from services.preview import preview_page
from services.preview_navigation import comparison_preview
from services.ai_bridge import AIIntegrationError
from services.archive_site import ArchiveError
from services.archive_fallback import recover_from_url
from services.security import UnsafeURL
from services.local_ai import redesign_with_local_gemma
from services.redesign import modernize_site

st.set_page_config(page_title='404 Afterlife | Real Website Modernization', page_icon='🕸️', layout='wide')
st.title('🕸️ 404 AFTERLIFE')
st.caption('Dead websites, reborn • Keep the real pages, content and assets')
st.write('Upload a complete old website ZIP, or recover an archived website. We try Wayback first, then Arquivo.pt if needed. Compare **the same page** before and after, then download the entire website.')

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
    st.caption('Automatic archive fallback: Wayback → Arquivo.pt. Availability and capture dates may differ between archives.')
    archive_year_mode = st.radio('Archive year', ['Automatic (closest)', 'Choose Year'],horizontal=True)
    if archive_year_mode == 'Choose Year':
        chosen_year = st.selectbox('Choose archive year', list(range(date.today().year,1995,-1)), index=16)

method = st.radio('Redesign method', ['Local Gemma (Ollama)', 'Safe CSS refresh (works now)'], horizontal=True)
if method == 'Local Gemma (Ollama)':
    st.caption('Powered by Gemma via Ollama. Keep Ollama running while your website is processed.')
else:
    st.caption('Refresh the design with CSS. This option works without Ollama and does not use AI.')

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
                original = recover_from_url(url, chosen_year)
            report_before = analyze_site(original)
        with st.spinner('Redesigning your website...'):
            if method == 'Local Gemma (Ollama)':
                revised = redesign_with_local_gemma(original)
                method_label = 'Local Gemma (gemma3:1b via Ollama) — AI design selection'
            else:
                revised = modernize_site(original)
                method_label = 'CSS refresh — NOT AI'
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
    online_count=after_report.get('online_archive_link_count',0)
    if online_count:
        st.info(f'{online_count} link(s) point to pages not included in this ZIP. They open archived copies online; their availability is not verified.')
    st.caption(f"Source: {original.source.upper()}  •  Homepage: {original.homepage}  •  Redesign: {result['method']}")
    if original.source in ('wayback', 'arquivo') and original.recovery:
        rec = original.recovery
        capture = rec['capture']
        st.subheader('🕰️ Archive date & recovery coverage')
        provider = capture.get('provider', 'Wayback Machine')
        st.write(f"**Archive source:** {provider}")
        st.write(f"**Selected capture:** {capture['date_utc']}")
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
        st.download_button('⬇️ Download archive recovery report (JSON)',
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
    if after_report.get('link_issues'):
        with st.expander('Broken link details — missing files or anchors'):
            st.json(after_report['link_issues'])
    with st.expander('🔍 Full-site analysis (all pages)'):
        st.json(report)
    st.divider()
    st.subheader('🌐 Before / After — Same Original Page')
    st.caption('Click a link in either preview: both views follow the same page. Back and Home also stay synchronized.')
    chosen_page = st.selectbox('Choose which original page to compare',original.pages,
                                index=original.pages.index(original.homepage))
    components.html(comparison_preview(original,revised,chosen_page),height=720,scrolling=False)
    st.caption('Website scripts and form submissions remain disabled. Online archive links open a separate tab and may be unavailable; internal navigation stays within the sanitized preview.')
    st.divider()
    st.subheader('📦 Download the complete real website')
    result_id = hashlib.sha256(b''.join(path.encode() + b'\0' + hashlib.sha256(raw).digest() for path, raw in sorted(revised.files.items()))).hexdigest()[:10]
    st.caption(f'Result ID: {result_id} — this code also appears in the redesigned ZIP filename.')
    st.caption('The redesigned ZIP contains the exact result shown above. Extract the entire ZIP before opening its homepage. Screen size, source scripts and external assets can affect rendering outside this static preview.')
    left,right = st.columns(2)
    with left:
        st.download_button('⬇️ Download redesigned website ZIP', data=to_zip(revised),
                           file_name=f'404_afterlife_redesigned_{result_id}.zip',mime='application/zip',
                           use_container_width=True)
    with right:
        st.download_button('⬇️ Download original website ZIP', data=to_zip(original),
                           file_name='404_afterlife_original_site.zip',mime='application/zip',
                           use_container_width=True)

st.divider()
st.caption('Hackathon prototype • Only upload websites you have permission to modify • Archive recovery can be incomplete.')
