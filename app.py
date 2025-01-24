import streamlit as st
import index
import mutation_freq
import variant_deconv
import resistance_mut
import resistance_mut_silo
import genspectrum

PAGES = {
    "Home": {"module": index}, 
    "Mutation Frequency": {"module": mutation_freq},
    "Variant Deconvolution": {"module": variant_deconv},
    "Resistance Mutations (clinical)": {"module": resistance_mut},
    "Resistance Mutations (ww)": {"module": resistance_mut_silo},
    "Genspectrum": {"module": genspectrum}
}

def sidebar():
    # Add the logo and "powered by" text
    st.sidebar.markdown(
        """
        <div style="text-align: center;">
            <picture>
                <source
                    media="(prefers-color-scheme: light)"  
                    srcset="https://cbg-ethz.github.io/V-pipe/assets/img/logo-vpipe.svg">
                <source
                    media="(prefers-color-scheme: dark)"  
                    srcset="https://cbg-ethz.github.io/V-pipe/assets/img/logo-vpipe-dark.svg">
                <img alt="Logo" src="https://cbg-ethz.github.io/V-pipe/assets/img/logo-vpipe.svg" width="50%" />
            </picture>
            <p>on cloud</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Go to", list(PAGES.keys()))  # Changed to selectbox
    return selection

if __name__ == "__main__":
    st.set_page_config(page_title="V-Pipe Cloud", page_icon="https://cbg-ethz.github.io/V-pipe/favicon-32x32.png")
    selection = sidebar()
    page = PAGES[selection]["module"]
    page.app()