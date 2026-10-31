import streamlit as st
import streamlit.components.v1 as components

from services.security import validate_public_url, UnsafeURL
from services.archive import find_snapshot, fetch_snapshot_html, ArchiveError
from services.reconstruct import extract_content, create_fallback
from services.analyzer import analyze_website
from services.ai_redesign import redesign_website, AIRedesignError


# =====================================
# PAGE CONFIGURATION
# =====================================

st.set_page_config(
    page_title="404 Afterlife",
    page_icon="🕸️",
    layout="wide"
)

st.title("🕸️ 404 AFTERLIFE")
st.caption("Dead websites, reborn with AI · Hackathon MVP")

st.info(
    "Recover archived website content, analyze its structure, "
    "and prepare it for a modern AI-powered redesign."
)


# =====================================
# WEBSITE URL
# =====================================

url = st.text_input(
    "Website URL",
    placeholder="https://example.com/old-page"
)


# =====================================
# ARCHIVE SELECTION
# =====================================

archive_mode = st.radio(
    "Archive Selection",
    ["Automatic", "Choose Year"],
    horizontal=True
)

selected_year = None

if archive_mode == "Choose Year":
    selected_year = st.selectbox(
        "Select Archive Year",
        options=list(range(2026, 1995, -1)),
        index=16
    )


# =====================================
# SESSION STATE
# =====================================

if "result" not in st.session_state:
    st.session_state.result = None


# =====================================
# REVIVE WEBSITE
# =====================================

if st.button("♻️ Revive Website", type="primary"):

    st.session_state.result = None

    try:
        # STEP 1: Validate URL
        validated = validate_public_url(url)

        # STEP 2: Find archived snapshot
        with st.spinner("Searching for an archived snapshot..."):
            snapshot = find_snapshot(
                validated,
                year=selected_year
            )

        # STEP 3: No snapshot found
        if snapshot is None:

            st.warning(
                "No archived snapshot was found. "
                "We cannot recover the original content."
            )

            st.session_state.result = {
                "html": create_fallback(validated),
                "snapshot": None,
                "content": None,
                "analysis": None,
                "original_html": None,
                "method": "fallback"
            }

        # STEP 4: Snapshot found
        else:

            with st.spinner("Retrieving and analyzing archived content..."):

                source_html = fetch_snapshot_html(snapshot)

                content = extract_content(source_html)

                analysis = analyze_website(
                    source_html,
                    validated
                )

            # STEP 5: Prepare data for AI
            website_data = {
                "url": validated,
                "year": snapshot["year"],
                "content": content,
                "analysis": analysis
            }

            # STEP 6: Call AI redesign integration
            with st.spinner("Preparing website redesign..."):

                redesign_result = redesign_website(website_data)

                reconstructed = redesign_result["html"]

            # STEP 7: Save results
            st.session_state.result = {
                "html": reconstructed,
                "snapshot": snapshot,
                "content": content,
                "analysis": analysis,
                "original_html": source_html,
                "method": redesign_result.get("method", "fallback")
            }

            st.success("Website reconstruction completed.")

    except (UnsafeURL, ArchiveError, AIRedesignError, ValueError) as exc:
        st.error(str(exc))

    except Exception as exc:
        st.error(f"Error: {type(exc).__name__}: {exc}")
        st.exception(exc)


# =====================================
# DISPLAY RESULTS
# =====================================

result = st.session_state.result

if result:

    # =====================================
    # REDESIGN STATUS
    # =====================================

    if result.get("method") == "ai":

        st.success(
            "✨ Website successfully redesigned using AI!"
        )

    else:

        st.warning(
            "AI redesign is not connected yet. "
            "Showing the basic reconstruction template."
        )

    # =====================================
    # ARCHIVE INFORMATION
    # =====================================

    if result["snapshot"]:

        st.write(
            f"**Archive year:** {result['snapshot']['year']}"
        )

        st.write(
            f"**Redesign method:** {result.get('method', 'fallback')}"
        )

        st.write(
            f"**Extracted headings:** "
            f"{len(result['content']['headings'])}"
        )

        st.write(
            f"**Extracted paragraphs:** "
            f"{len(result['content']['paragraphs'])}"
        )

    # =====================================
    # WEBSITE ANALYSIS
    # =====================================

    if result.get("analysis"):

        analysis = result["analysis"]

        st.divider()
        st.subheader("🔍 Website Analysis")

        st.write("**Detected Layout:**")
        st.json(analysis["layout"])

        st.write("**HTML Elements:**")
        st.json(analysis["elements"])

        st.write("**Detected Colors:**")
        st.write(analysis["colors"])

        st.write("**Common CSS Classes:**")
        st.write(analysis["classes"])

        st.write("**Images Found:**")
        st.write(len(analysis["images"]))

        st.write("**Page Structure:**")
        st.json(analysis["page_structure"])

    # =====================================
    # BEFORE & AFTER COMPARISON
    # =====================================

    st.divider()
    st.subheader("🌐 Before & After Comparison")

    before_tab, after_tab = st.tabs([
        "🕰️ Before — Archived Website",
        "✨ After — Redesigned Website"
    ])

    # =====================================
    # BEFORE — ORIGINAL WEBSITE
    # =====================================

    with before_tab:

        st.caption(
            "Explore the original archived website from Wayback Machine."
        )

        if result.get("snapshot"):

            archive_url = result["snapshot"]["archive_url"]

            st.success(
                f"Original website archived in "
                f"{result['snapshot']['year']}."
            )

            st.link_button(
                "🕰️ View Original Archived Website",
                archive_url,
                use_container_width=True
            )

            st.info(
                "The original website opens in a new browser tab. "
                "Return here to compare it with the redesigned version."
            )

        else:

            st.warning("No archived version is available.")

    # =====================================
    # AFTER — REDESIGNED WEBSITE
    # =====================================

    with after_tab:

        if result.get("method") == "ai":

            st.caption(
                "Modern website redesign generated using AI."
            )

        else:

            st.caption(
                "Basic reconstruction preview. "
                "AI redesign will replace this template."
            )

        components.html(
            result["html"],
            height=650,
            scrolling=True
        )

    # =====================================
    # DOWNLOAD HTML
    # =====================================

    st.download_button(
        "⬇️ Download Redesigned HTML",
        data=result["html"],
        file_name="404_afterlife_redesign.html",
        mime="text/html"
    )


# =====================================
# FOOTER
# =====================================

st.divider()

st.caption(
    "Educational prototype. Archived content and generated "
    "designs should be reviewed before reuse."
)