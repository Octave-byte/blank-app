import streamlit as st
from routing.route_finder import find_best_routes_parallel

# Allowed chains
CHAIN_OPTIONS = ["Ethereum", "Base", "Arbitrum", "Polygon", "Berachain", "Gnosis", "Optimism", "Lisk", "Taiko", "Rootstock", "Sonic", "Soneium", "Corn"]

st.title("Jumper Route Finder")

# Inputs 
col1, col2 = st.columns(2)
with col1:
    src_chain = st.selectbox("Source Chain", CHAIN_OPTIONS)
    src_token = st.text_input("Source Token (symbol or address)", value="USDC")
with col2:
    dst_chain = st.selectbox("Destination Chain", CHAIN_OPTIONS)
    dst_token = st.text_input("Destination Token (symbol or address)", value="ETH")

amount = st.number_input("Amount to Send", min_value=0.0, step=0.1, value=1.0)

# Selection for route preference
route_preference = st.radio(
    "Route Preference",
    options=["CHEAPEST", "FASTEST"],
    index=0,
    horizontal=True
)

if st.button("Compute Best Route"):

    with st.spinner("Finding best route..."):

        try:
            result = find_best_routes_parallel(
                src_chain_name=src_chain,
                dst_chain_name=dst_chain,
                src_token=src_token,
                dst_token=dst_token,
                amount=amount,
                order = route_preference
            )

            best = result.get("best")
            alternatives = result.get("alternatives", [])

            if not best:
                st.error("No valid route found.")
            else:
                st.subheader("✅ Best Route")
                st.write(f"**Type**: {best['type']}")
                st.write(f"**Description**: {best['description']}")

                for i, step in enumerate(best["steps"], 1):
                    with st.expander(f"Step {i} - {step.get('tool', 'N/A')}"):
                        st.write(f"**Expected Amount**: {step.get('expectedAmount')}")
                        st.write(f"**Efficiency**: {step.get('efficiency'):.4%}")
                        st.write(f"**Execution Time**: {step.get('time')} seconds")
                        st.write(f"**Jumper Link**: {step.get('link')}")

                if alternatives:
                    st.subheader("💡 Alternative Routes")
                    for alt in alternatives:
                        with st.expander(f"{alt['type']} - Efficiency: {alt['efficiency']}"):
                            st.write(alt["description"])
                            for j, step in enumerate(alt["steps"], 1):
                                st.write(f"- Step {j}: {step.get('tool', 'N/A')}, Expected: {step.get('expectedAmount')}, Efficiency: {step.get('efficiency'):.4%}, Time: {step.get('time')}s, Jumper Link:{step.get('link')} ")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")