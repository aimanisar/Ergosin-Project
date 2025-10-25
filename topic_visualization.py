#!/usr/bin/env python3
"""
Topic Visualization Module for Competitive Intelligence Dashboard.

This module provides comprehensive data visualization capabilities:
- Interactive topic comparison charts
- Competitive analysis visualizations
- Market trend analysis
- Strategic insights dashboards
"""

import re
from collections import Counter
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from config import SITES
# from main import get_cached_data
from storage import load_cache
from urllib.parse import urlparse
import ast
import networkx as nx
import streamlit as st
from storage import load_cache
from collections import Counter
import ast

@st.cache_data(
    show_spinner=False,
    hash_funcs={
        list: lambda _: None,
        dict: lambda _: None,
        pd.DataFrame: lambda _: None
    }
)
def get_cached_data():
    """Load cached data safely for visualizations."""
    return load_cache()


def apply_plotly_theme(fig, mode="light"):
    """Unified plotly styling for light/dark dashboard modes"""
    if mode == "dark":
        fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font=dict(color="#e2e8f0", size=13),
        legend=dict(bgcolor="#1e293b", font=dict(color="#e2e8f0")),
    )
    else:
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            font=dict(color="#1e293b", size=13),
            legend=dict(bgcolor="#ffffff", font=dict(color="#1e293b")),
        )
    return fig


class TopicVisualizer:
    def __init__(self):
        self.df = None
        self.base_data = None
        self.competitor_data = None


    def _extract_netloc(self, url):
            """Return lower-cased netloc (domain) for a URL or host-like string."""
            if not isinstance(url, str) or url.strip() == "":
                return ""
            u = url.strip()
            if "://" in u:
                net = urlparse(u).netloc
            else:
                net = u.split("/")[0]
            return net.lower().replace("www.", "").strip()


    def _match_sites(self, df, site_list):
            """Match rows by normalized netlocs (uses website_netloc created in load_data).
            Returns a safe copy and avoids drop_duplicates() to prevent errors with unhashable columns.
            """
            nets = [self._extract_netloc(s) for s in site_list]
            matched = df[df.get("website_netloc", pd.Series(dtype="object")).isin(nets)].copy()
            return matched.reset_index(drop=True)


    # def _match_sites(self, df, site_list):
    #     """Match websites flexibly, ignoring www. and subdomain variations."""
    #     matched = pd.DataFrame()
    #     for s in site_list:
    #         pattern = s.replace("www.", "")
    #         temp = df[df["website_clean"].str.contains(pattern, case=False, na=False)]
    #         matched = pd.concat([matched, temp], ignore_index=True)

    #     # Drop duplicates safely (ignore unhashable columns like 'topics')
    #     dedup_columns = [c for c in matched.columns if c != "topics"]
    #     return matched.drop_duplicates(subset=dedup_columns, keep="first").reset_index(drop=True)

    def load_data(self, df=None, filter_type=None):
        """Load cached data and optionally filter by competitor type"""
        self.filter_type = filter_type 
        
        if df is None:
            df = get_cached_data()
        if df is None or df.empty:
            st.info("No data available for visualization.")
            return False
        if "topics" in df.columns:
            def clean_topics(x):
                """Normalize topic entries to clean strings."""
                if isinstance(x, list):
                    return [t.strip().strip("[]'\"") for t in x if str(t).strip()]
                if isinstance(x, str):
                    # Try parsing list-like strings safely
                    try:
                        parsed = ast.literal_eval(x)
                        if isinstance(parsed, list):
                            return [t.strip().strip("[]'\"") for t in parsed if str(t).strip()]
                    except Exception:
                        pass
                    # Fallback: split by comma
                    return [t.strip().strip("[]'\"") for t in x.split(",") if str(t).strip()]
                return [],

            df["topics"] = df["topics"].apply(clean_topics)
            # Preserve original topics for display
            df["topics"] = df["topics"].apply(
                lambda topics: [str(t).strip() for t in topics if isinstance(t, (str, int, float))]
            )

            # Add lowercase-normalised version for matching
            df["_topics_lower"] = df["topics"].apply(
                lambda topics: [t.lower() for t in topics]
            )

        df["website_netloc"] = df["website"].apply(self._extract_netloc)

        # --- Build competitor groups dynamically from config, cleaned ---
        # Build competitor groups from config (raw), matching will use netlocs
        close_sites = [s.get("url", "") for s in SITES if s.get("type") == "competitor_close"]
        international_sites = [s.get("url", "") for s in SITES if s.get("type") == "competitor_international"]

        # Base website = ergosign (match on normalized netloc)
        self.base_data = df[df["website_netloc"].str.contains("ergosign", case=False, na=False)]

        # Filter competitors by type (using robust match on website_netloc)
        if filter_type == "close":
            self.competitor_data = self._match_sites(df, close_sites)
        elif filter_type == "international":
            self.competitor_data = self._match_sites(df, international_sites)
        else:
            competitor_sites = close_sites + international_sites
            self.competitor_data = self._match_sites(df, competitor_sites)

        self.df = df

        # --- Debug logging ---
        print(f"DEBUG — Loaded data shape: {df.shape}")
        print(f"DEBUG — Base sites found (netloc): {self.base_data['website_netloc'].unique().tolist()}")
        print(f"DEBUG — Competitors ({filter_type}) (netloc): {self.competitor_data['website_netloc'].unique().tolist()}")
        # st.write("✅ Loaded sites (netloc):", df["website_netloc"].unique().tolist())
        # st.write("🔍 Raw website values in cached data:", df["website"].unique().tolist())
        # st.write("🔍 Preview of topics column:")
        # st.write(df["topics"].head(10))
        return True
    
    # def load_data(self, df=None, filter_type=None):
    #     """Load cached data and optionally filter by competitor type"""
    #     self.filter_type = filter_type 
        
    #     if df is None:
    #         from storage import load_cache
    #         df = load_cache()
    #     if df is None or df.empty:
    #         st.info("No data available for visualization.")
    #         return False

    #     # --- Normalize website column for matching ---
    #     df['website_clean'] = (
    #         df['website']
    #         .str.replace(r'^https?://', '', regex=True)   # remove http:// or https://
    #         .str.replace(r'^www\.', '', regex=True)       # remove leading www.
    #         .str.strip('/')                               # remove trailing slash
    #     )

    #     # Build competitor groups dynamically from config, also cleaned
    #     close_sites = [s["url"].replace("https://", "").replace("http://", "").replace("www.", "").strip('/') for s in SITES if s["type"] == "competitor_close"]
    #     international_sites = [s["url"].replace("https://", "").replace("http://", "").replace("www.", "").strip('/') for s in SITES if s["type"] == "competitor_international"]

    #         # Base website = ergosign
    #     self.base_data = df[df["website_clean"].str.contains("ergosign", case=False, na=False)]

    #         # Filter competitors by type
    #     if filter_type == "close":
    #         self.competitor_data = _match_sites(df, close_sites)
    #     elif filter_type == "international":
    #         self.competitor_data = _match_sites(df, international_sites)
    #     else:
    #         competitor_sites = close_sites + international_sites
    #         self.competitor_data = _match_sites(df, competitor_sites)   

    #     self.df = df

    #     self.df = df

    #     # Debug logging
    #     print(f"DEBUG — Loaded data shape: {df.shape}")
    #     print(f"DEBUG — Base sites found: {self.base_data['website_clean'].unique().tolist()}")
    #     print(f"DEBUG — Competitors ({filter_type}): {self.competitor_data['website_clean'].unique().tolist()}")
    #     print(f"DEBUG — Competitors found ({filter_type}): {self.competitor_data['website_clean'].unique().tolist()}")

    #     st.write("✅ Loaded sites:", df["website_clean"].unique().tolist())


    #     return True


    def extract_topics(self, data):
        """Extract and count topics from data"""
        all_topics = []
        for topics_str in data['topics'].dropna():
            if topics_str and topics_str != '[]':
                # Split by comma and clean up
                topics = [topic.strip() for topic in str(topics_str).split(',')]
                all_topics.extend(topics)
        
        # Count topic frequency
        topic_counts = Counter(all_topics)
        return topic_counts
    
    def create_simple_topic_comparison(self, competitor_type="default"):
        """Create a simple, realistic topic comparison"""
        if self.base_data.empty or self.competitor_data.empty:
            st.warning("Need both base and competitor data for comparison")
            return
        
        # Extract topics
        base_topics = self.extract_topics(self.base_data)
        competitor_topics = self.extract_topics(self.competitor_data)
        
        # Get top 15 topics for each
        top_base = dict(base_topics.most_common(15))
        top_competitor = dict(competitor_topics.most_common(15))
        
        # Create comparison data
        all_topics = set(list(top_base.keys()) + list(top_competitor.keys()))
        
        comparison_data = []

        # Pre-flatten competitor topics once for performance
        competitor_topic_map = {}
        for w in self.competitor_data['website'].unique():
            site_topics = self.competitor_data[self.competitor_data['website'] == w]['_topics_lower']
            flattened = []
            for t in site_topics:
                if isinstance(t, list):
                    flattened.extend([tt.strip().lower() for tt in t if tt.strip()])
                elif isinstance(t, str):
                    flattened.extend([tt.strip().lower() for tt in t.split(',') if tt.strip()])
            competitor_topic_map[w] = set(flattened)  # deduplicate per website

        for topic in all_topics:
            topic_display = str(topic).strip("[]'\"").title()  # keep CamelCase for visuals
            topic_clean = topic_display.lower()

            base_count = top_base.get(topic, 0)
            comp_count = top_competitor.get(topic, 0)
            total_count = base_count + comp_count

            # Find which competitors mention this topic (case-insensitive)
            mentioned_by = [
                w for w, topics in competitor_topic_map.items()
                if topic_clean in topics
            ]

            comparison_data.append({
                'Topic': topic_display,
                'Base Website': base_count,
                'Competitors': comp_count,
                'Total': total_count,
                'Mentioned By': ", ".join(sorted(mentioned_by)) if mentioned_by else "—"
            })

        comparison_df = pd.DataFrame(comparison_data)
        comparison_df = comparison_df.sort_values('Total', ascending=True)

        # --- Plot ---
        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=comparison_df['Topic'],
            x=comparison_df['Base Website'],
            name='Ergosin',
            orientation='h',
            marker_color="#2f8288",
            text=comparison_df['Base Website'],
            hovertemplate="<b>%{y}</b><br>Mentions: %{x}<br>Source: Ergosign<extra></extra>",
        ))

        fig.add_trace(go.Bar(
            y=comparison_df['Topic'],
            x=comparison_df['Competitors'],
            name='Competitors',
            orientation='h',
            marker_color="#9E3900",
            text=comparison_df['Competitors'],
            hovertemplate="<b>%{y}</b><br>Mentions: %{x}<br><b>Mentioned by:</b> %{customdata}<extra></extra>",
            customdata=comparison_df['Mentioned By']
        ))

        fig.update_layout(
            title='Topic Comparison: Your Website vs Competitors',
            xaxis_title='Number of Mentions',
            yaxis_title='Topics',
            barmode='group',
            height=max(600, len(comparison_df) * 25),
            showlegend=True,
            template='plotly_white',
            margin=dict(l=200, r=50, t=80, b=50)
        )

        st.plotly_chart(fig, use_container_width=True, key=f"plot_{competitor_type}_{id(fig)}")

        # # --- Table below the chart ---
        # st.markdown("### 🔍 Competitors Mentioning Each Topic")
        # st.dataframe(
        #     comparison_df[['Topic', 'Mentioned By', 'Competitors']],
        #     use_container_width=True
        # )

        # --- Simple insights ---
        # st.subheader("Key Findings")
        # col1, col2 = st.columns(2)
        # with col1:
        #     st.write("**Your Top Topics:**")
        #     for topic, count in base_topics.most_common(5):
        #         st.write(f"• {topic}: {count} mentions")

        # with col2:
        #     st.write("**Competitor Top Topics:**")
        #     for topic, count in competitor_topics.most_common(5):
        #         st.write(f"• {topic}: {count} mentions")
        
    def create_website_analysis_chart(self, competitor_type="default"):
        """Create a comprehensive website analysis chart"""
        if self.df.empty:
            return
        
        # Group by website
        website_stats = []
        for website in self.df['website'].unique():
            website_data = self.df[self.df['website'] == website]
            
            # Extract topics
            all_topics = []
            for topics_str in website_data['topics'].dropna():
                if topics_str and topics_str != '[]':
                    topics = [topic.strip() for topic in str(topics_str).split(',')]
                    all_topics.extend(topics)
            
            website_type = 'Base' if 'ergosign' in website.lower() else 'Competitor'
            
            website_stats.append({
                'Website': website,
                'Type': website_type,
                'Total Pages': len(website_data),
                'Unique Topics': len(set(all_topics)),
                'Total Topic Mentions': len(all_topics),
                'Avg Topics per Page': len(all_topics) / len(website_data) if len(website_data) > 0 else 0
            })
        
        stats_df = pd.DataFrame(website_stats)
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Total Pages', 'Unique Topics', 'Total Topic Mentions', 'Avg Topics per Page'),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}]]
        )
        
        # Color mapping
        colors = ['#1f77b4' if t == 'Base' else '#ff7f0e' for t in stats_df['Type']]
        
        # Add traces
        fig.add_trace(
            go.Bar(x=stats_df['Website'], y=stats_df['Total Pages'], 
                   name='Pages', marker_color=colors, showlegend=False),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(x=stats_df['Website'], y=stats_df['Unique Topics'], 
                   name='Topics', marker_color=colors, showlegend=False),
            row=1, col=2
        )
        
        fig.add_trace(
            go.Bar(x=stats_df['Website'], y=stats_df['Total Topic Mentions'], 
                   name='Mentions', marker_color=colors, showlegend=False),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(x=stats_df['Website'], y=stats_df['Avg Topics per Page'], 
                   name='Avg Topics', marker_color=colors, showlegend=False),
            row=2, col=2
        )
        
        fig.update_layout(
            title='Website Analysis Overview',
            height=700,  # Increased height
            template='plotly_white',
            showlegend=False,
            margin=dict(l=50, r=50, t=80, b=150)  # Add bottom margin for rotated labels
        )
        
        # Rotate x-axis labels and improve spacing
        fig.update_xaxes(
            tickangle=-45,
            tickfont=dict(size=9)
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"plot_{competitor_type}_{id(fig)}")

    
    
    def create_professional_analysis(self):
        """Create professional business analytics visualizations"""
        if self.df.empty:
            return
        
        # st.subheader("Competitive Analysis Dashboard")
        
        # Identify base website
        base_website = None
        for website in self.df['website'].unique():
            if 'ergosign' in website.lower():
                base_website = website
                break
        
        if not base_website:
            st.warning("Base website (ergosign) not found in data")
            return
        
        # ✅ Use only filtered competitor data for the current tab
        competitor_websites = self.competitor_data['website'].unique()
        
        if len(competitor_websites) == 0:
            st.info(f"No competitors found for {self.filter_type} group")
            return
        
        # Collect topics
        website_topics = {}
        
        # Base
        base_topics = []
        for topics_str in self.base_data['topics'].dropna():
            if topics_str and topics_str != '[]':
                base_topics.extend([t.strip() for t in str(topics_str).split(',')])
        website_topics[base_website] = list(set(base_topics))
        
        # Competitors
        for website in competitor_websites:
            website_data = self.competitor_data[self.competitor_data['website'] == website]
            topics = []
            for topics_str in website_data['topics'].dropna():
                if topics_str and topics_str != '[]':
                    topics.extend([t.strip() for t in str(topics_str).split(',')])
            website_topics[website] = list(set(topics))
        
        # Now generate charts
        # self._create_topic_coverage_heatmap(
        #     website_topics, base_website, competitor_websites, competitor_type=self.filter_type
        # )
        # self._create_competitive_positioning_chart(
        #     website_topics, base_website, competitor_websites, competitor_type=self.filter_type
        # )
        # Extra easy-to-read visuals
        self._create_topic_frequency_chart(website_topics, competitor_type=self.filter_type)
        # self._create_topic_distribution_pie(website_topics, competitor_type=self.filter_type)
        # Priority analysis
        all_topics = set()
        for topics in website_topics.values():
            all_topics.update(topics)

        self._create_topic_priority_list(
            topics=all_topics,
            website_topics=website_topics,
            base_website=base_website
        )
        # New Treemap Visualization
        # self._create_competitor_topic_treemap(website_topics, competitor_type=self.filter_type)



    
    

    def _create_topic_frequency_chart(self, website_topics, competitor_type="default"):
        """Interactive horizontal bar chart of top topics among competitors with filters and tooltips"""

        # --- Step 1: Flatten topics across competitors ---
        all_records = []
        for site, topics in website_topics.items():
            if site not in self.base_data["website"].unique():  # exclude base Ergonsign
                for topic in topics:
                    all_records.append({"Website": site, "Topic": topic})

        if not all_records:
            st.info(f"No topics available for {competitor_type} competitors.")
            return

        df = pd.DataFrame(all_records)

        # --- Step 2: Add Filters ---
        competitors = sorted(df["Website"].unique())
        selected_competitors = st.multiselect(
            "Select competitors to include:",
            competitors,
            default=competitors
        )

        topics_all = sorted(df["Topic"].unique())
        selected_topics = st.multiselect(
            "Filter by topics (optional):",
            topics_all,
            default=topics_all[:15]
        )

        filtered_df = df[
            (df["Website"].isin(selected_competitors)) &
            (df["Topic"].isin(selected_topics))
        ]

        # --- Step 3: Compute frequency + coverage ---
        topic_stats = (
            filtered_df.groupby("Topic")
            .agg(
                Mentions=("Website", "count"),
                UniqueWebsites=("Website", pd.Series.nunique)
            )
            .reset_index()
        )
        topic_stats["Coverage %"] = (
                pd.to_numeric(topic_stats["UniqueWebsites"], errors="coerce")
                / float(len(selected_competitors))
                * 100
            )
        topic_stats["Coverage %"] = topic_stats["Coverage %"].astype(float).round(1)


        # --- Step 4: Plotly Chart ---
        fig = px.bar(
            topic_stats.sort_values("Mentions", ascending=True).head(20),
            x="Mentions",
            y="Topic",
            orientation="h",
            color="Coverage %",
            color_continuous_scale="Blues",
            hover_data={
                "Mentions": True,
                "Coverage %": True,
                "Topic": False
            },
            labels={
                "Mentions": "Mentions across selected competitors",
                "Coverage %": "Coverage (%) of competitors discussing topic",
                "Topic": "Topic"
            },
            title=f"Competitive Topic Frequency — {competitor_type.capitalize()} Competitors"
        )

        fig.update_traces(
            hovertemplate="<b>%{y}</b><br>Mentions: %{x}<br>Coverage: %{marker.color:.1f}%<extra></extra>",
            text=topic_stats["Mentions"],
            textposition="inside",
            insidetextanchor="middle"
        )

        fig.update_layout(
            xaxis_title="Mentions",
            yaxis_title="Topic",
            coloraxis_colorbar=dict(title="Coverage (%)"),
            template="plotly_white",
            height=550,
            margin=dict(l=150, r=50, t=70, b=50)
        )

        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "📘 Hover to see each topic’s coverage (% of competitors discussing it). "
            "Use the filters above to narrow by specific competitors or topics."
        )



    
    # @st.cache_data(show_spinner=False, hash_funcs={list: lambda _: None})
    def _create_topic_priority_list(self, topics, website_topics, base_website):
        """Create a priority-ordered list of topics"""
        if not topics:
            st.warning("No topics match the current filters.")
            return
        # Calculate priority metrics
        priority_data = []
        ergosign_topics = set(website_topics.get(base_website, []))
        # Debug info
        st.caption(f"📊 Analyzing {len(topics)} topics across {len(website_topics)} websites")
        for topic in topics:
            competitor_mentions = sum(website_topics.get(website, []).count(topic) 
                                    for website in website_topics.keys() if website != base_website)
            ergosign_mentions = website_topics.get(base_website, []).count(topic)
            # Enhanced priority calculation with more nuanced logic
            if topic not in ergosign_topics:
                if competitor_mentions >= 5:
                    priority = "🔴 CRITICAL"
                    action = "URGENT: Start covering this high-impact topic"
                elif competitor_mentions >= 2:
                    priority = "🟠 HIGH"
                    action = "Start covering this topic"
                else:
                    priority = "🟡 MEDIUM"
                    action = "Consider covering this topic"
            elif ergosign_mentions < competitor_mentions:
                gap_ratio = competitor_mentions / ergosign_mentions if ergosign_mentions > 0 else competitor_mentions
                if gap_ratio >= 3:
                    priority = "🔴 CRITICAL"
                    action = f"URGENT: Increase coverage (behind by {competitor_mentions - ergosign_mentions})"
                elif gap_ratio >= 2:
                    priority = "🟠 HIGH"
                    action = f"Increase coverage (behind by {competitor_mentions - ergosign_mentions})"
                else:
                    priority = "🟡 MEDIUM"
                    action = f"Slightly increase coverage (behind by {competitor_mentions - ergosign_mentions})"
            elif ergosign_mentions == competitor_mentions:
                priority = "🟢 MEDIUM"
                action = "Maintain current position"
            else:
                lead_ratio = ergosign_mentions / competitor_mentions if competitor_mentions > 0 else ergosign_mentions
                if lead_ratio >= 2:
                    priority = "✅ LOW"
                    action = "Continue leading (strong position)"
                else:
                    priority = "🟢 LOW"
                    action = "Continue leading (slight advantage)"
            priority_data.append({
                'Topic': topic,
                'Priority': priority,
                'Action': action,
                'Ergosign': ergosign_mentions,
                'Competitors': competitor_mentions
            })
        # Enhanced sorting: Priority first, then by competitor mentions (higher activity first)
        priority_order = {"🔴 CRITICAL": 4, "🟠 HIGH": 3, "🟡 MEDIUM": 2, "🟢 MEDIUM": 1, "🟢 LOW": 0, "✅ LOW": 0}
        priority_data.sort(key=lambda x: (priority_order.get(x['Priority'], 0), -x['Competitors']), reverse=True)
        # Display as table
        df = pd.DataFrame(priority_data)
        # Enhanced color coding with proper text visibility
        def color_priority(val):
            if val == "🔴 CRITICAL":
                return 'background-color: #ffebee; color: #d32f2f; font-weight: bold'
            elif val == "🟠 HIGH":
                return 'background-color: #fff3e0; color: #f57c00; font-weight: bold'
            elif val == "🟡 MEDIUM":
                return 'background-color: #fffde7; color: #f9a825'
            elif val == "🟢 MEDIUM":
                return 'background-color: #e8f5e8; color: #388e3c'
            elif val == "🟢 LOW":
                return 'background-color: #f1f8e9; color: #689f38'
            else:  # ✅ LOW
                return 'background-color: #f3e5f5; color: #7b1fa2'
        styled_df = df.style.applymap(color_priority, subset=['Priority'])
        # Add summary statistics
        critical_count = len([p for p in priority_data if "🔴" in p['Priority']])
        high_count = len([p for p in priority_data if "🟠" in p['Priority']])
        medium_count = len([p for p in priority_data if "🟡" in p['Priority']])
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🔴 Critical", critical_count)
        with col2:
            st.metric("🟠 High Priority", high_count)
        with col3:
            st.metric("🟡 Medium Priority", medium_count)
        with col4:
            st.metric("Total Topics", len(priority_data))
        st.dataframe(styled_df, use_container_width=True)
        # Add insights
        if critical_count > 0:
            st.warning(f"⚠️ {critical_count} topics require immediate attention!")
        if high_count > 0:
            st.info(f"💡 {high_count} topics have high strategic value")

    
  
    # @st.cache_data(show_spinner=False, hash_funcs={list: lambda _: None})
    def create_priority_bubble_chart(self, competitor_type="default"):
        """Create a bubble chart to prioritize missing topics by importance"""
        if self.df.empty:
            return
        
        # Get all unique topics
        all_topics = []
        for topics_str in self.df['topics'].dropna():
            if topics_str and topics_str != '[]':
                topics = [topic.strip() for topic in str(topics_str).split(',')]
                all_topics.extend(topics)
        
        unique_topics = list(set(all_topics))
        if not unique_topics:
            st.warning("No topics found for bubble chart")
            return
        
        # Calculate metrics for each topic
        websites = self.df['website'].unique()
        base_website = websites[0] if len(websites) > 0 else None
        
        bubble_data = []
        for topic in unique_topics:
            # Count mentions across all websites
            total_mentions = 0
            competitor_mentions = 0
            websites_covering = 0
            
            for website in websites:
                website_data = self.df[self.df['website'] == website]
                website_topics = []
                
                for topics_str in website_data['topics'].dropna():
                    if topics_str and topics_str != '[]':
                        topics = [topic.strip() for topic in str(topics_str).split(',')]
                        website_topics.extend(topics)
                
                topic_count = website_topics.count(topic)
                total_mentions += topic_count
                
                if website == base_website:
                    base_mentions = topic_count
            else:
                competitor_mentions += topic_count
            
            if topic_count > 0:
                websites_covering += 1
            
            # Calculate priority score
            market_penetration = websites_covering / len(websites) * 100
            competitor_activity = competitor_mentions
            base_coverage = base_mentions if base_website else 0
            
            # Priority score: high market penetration + high competitor activity + low base coverage
            priority_score = (market_penetration * 0.4) + (competitor_activity * 0.4) + ((100 - base_coverage) * 0.2)
            
            bubble_data.append({
                'Topic': topic,
                'Market Penetration': market_penetration,
                'Competitor Activity': competitor_activity,
                'Base Coverage': base_coverage,
                'Priority Score': priority_score,
                'Total Mentions': total_mentions,
                'Websites Covering': websites_covering
            })
        
        bubble_df = pd.DataFrame(bubble_data)
        
        # Create bubble chart
        fig = go.Figure()
        
        # Color by priority score
        fig.add_trace(go.Scatter(
            x=bubble_df['Market Penetration'],
            y=bubble_df['Competitor Activity'],
            mode='markers+text',
            text=bubble_df['Topic'],
            textposition='top center',
            marker=dict(
                size=bubble_df['Total Mentions'] * 5,
                color=bubble_df['Priority Score'],
                colorscale='RdYlGn_r',
                showscale=True,
                colorbar=dict(title="Priority Score"),
                line=dict(width=1, color='black')
            ),
            hovertemplate='<b>%{text}</b><br>' +
                         'Market Penetration: %{x:.1f}%<br>' +
                         'Competitor Activity: %{y}<br>' +
                         'Priority Score: %{marker.color:.1f}<br>' +
                         'Total Mentions: %{marker.size}<br>' +
                         '<extra></extra>',
            name='Topics'
        ))
        
        fig.update_layout(
            title='Topic Priority Matrix - Bubble Chart',
            xaxis_title='Market Penetration (%)',
            yaxis_title='Competitor Activity (Mentions)',
            height=700,  # Increased height
            template='plotly_white',
            margin=dict(l=100, r=100, t=80, b=80)  # Add margins
        )
        
        # Improve text positioning to prevent overlapping
        fig.update_traces(
                textposition='top center',
            textfont=dict(size=8)  # Smaller text size
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"plot_{competitor_type}_{id(fig)}")

        
        # Priority recommendations
        st.subheader("🎯 Priority Recommendations")
        
        # Sort by priority score
        priority_df = bubble_df.sort_values('Priority Score', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🚀 High Priority (Missing + High Competitor Activity):**")
            high_priority = priority_df[
                (priority_df['Base Coverage'] == 0) & 
                (priority_df['Competitor Activity'] >= 2)
            ].head(5)
            
            for _, row in high_priority.iterrows():
                st.write(f"• **{row['Topic']}**: {row['Competitor Activity']} competitor mentions, {row['Market Penetration']:.1f}% market penetration")
        
        with col2:
            st.write("**⚡ Medium Priority (Low Coverage + Growing Market):**")
            medium_priority = priority_df[
                (priority_df['Base Coverage'] <= 1) & 
                (priority_df['Market Penetration'] >= 30)
            ].head(5)
            
            for _, row in medium_priority.iterrows():
                st.write(f"• **{row['Topic']}**: {row['Base Coverage']} current mentions, {row['Market Penetration']:.1f}% market penetration")
        
        # Market opportunity analysis
        st.markdown("---")
        st.subheader("📊 Market Opportunity Analysis")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_missing = len(priority_df[priority_df['Base Coverage'] == 0])
            st.metric("Topics We Don't Cover", total_missing)
        
        with col2:
            high_opportunity = len(priority_df[
                (priority_df['Base Coverage'] == 0) & 
                (priority_df['Competitor Activity'] >= 2)
            ])
            st.metric("High-Opportunity Topics", high_opportunity)
        
        with col3:
            avg_priority = priority_df['Priority Score'].mean()
            st.metric("Average Priority Score", f"{avg_priority:.1f}")


    

    # def display_metrics(self):
    #     """Display key metrics"""
    #     if self.df.empty:
    #         return
        
    #     col1, col2, col3, col4 = st.columns(4)
        
    #     with col1:
    #         st.metric("Total Websites", len(self.df['website'].unique()))
        
    #     with col2:
    #         st.metric("Total Pages", len(self.df))
        
    #     with col3:
    #         all_topics = []
    #         for topics_str in self.df['topics'].dropna():
    #             if topics_str and topics_str != '[]':
    #                 topics = [topic.strip() for topic in str(topics_str).split(',')]
    #                 all_topics.extend(topics)
    #         st.metric("Unique Topics", len(set(all_topics)))
        
    #     with col4:
    #         base_pages = len(self.base_data) if not self.base_data.empty else 0
    #         competitor_pages = len(self.competitor_data) if not self.competitor_data.empty else 0
    #         st.metric("Base vs Competitor Pages", f"{base_pages} : {competitor_pages}")
    
    # @st.cache_data(show_spinner=False, hash_funcs={list: lambda _: None})

    # ---- Cached helper for data preparation ----
    @st.cache_data(show_spinner=False)
    def _prepare_treemap_data(_self, website_topics):
        """Cached data preprocessing only (safe for caching)."""
        all_records = []
        for site, topics in website_topics.items():
            # Flatten any nested lists or tuples
            flat_topics = []
            for t in topics:
                if isinstance(t, (list, tuple)):
                    flat_topics.extend([str(x).strip() for x in t])
                else:
                    flat_topics.append(str(t).strip())
            for topic in flat_topics:
                if topic:
                    all_records.append({"Website": site, "Topic": topic})

        if not all_records:
            return pd.DataFrame(columns=["Website", "Topic", "Mentions"])

        df = pd.DataFrame(all_records)
        return df.groupby(["Website", "Topic"]).size().reset_index(name="Mentions")

    def _create_competitor_topic_treemap(self, website_topics, competitor_type="default"):
        """Treemap visualization for topic distribution with dynamic filters (dropdown + slider)."""

        # --- Prepare data ---
        all_records = []
        for site, topics in website_topics.items():
            for topic in topics:
                all_records.append({"Website": site, "Topic": topic})

        if not all_records:
            st.info(f"No topics available for {competitor_type} competitors.")
            return

        topic_stats = (
            pd.DataFrame(all_records)
            .groupby(["Website", "Topic"])
            .size()
            .reset_index(name="Mentions")
        )

        # --- Layout: Title + Filters in One Row ---
        st.markdown("### Treemap of Topic Distribution")

        col1, col2, col3, col4 = st.columns([1, 2, 2, 1])  # balanced center layout
        with col2:
            competitors = sorted(topic_stats["Website"].unique())
            selected_competitors = st.multiselect(
                "Select Competitors",
                options=competitors,
                default=[competitors[0]] if competitors else [],
                key=f"treemap_filter_{competitor_type}"
            )
        with col3:
            top_n = st.slider(
                "Top N Topics",
                min_value=5,
                max_value=30,
                value=10,
                step=1,
                key=f"treemap_topn_{competitor_type}"
            )

        # --- Reactive filtering ---
        if not selected_competitors:
            st.warning("Please select at least one competitor.")
            return

        filtered_df = topic_stats[topic_stats["Website"].isin(selected_competitors)]
        top_topics = (
            filtered_df.groupby("Topic")["Mentions"]
            .sum()
            .nlargest(top_n)
            .index
        )
        filtered_df = filtered_df[filtered_df["Topic"].isin(top_topics)]

        # --- Treemap Visualization ---
        fig = px.treemap(
            filtered_df,
            path=["Website", "Topic"],
            values="Mentions",
            color="Mentions",
            color_continuous_scale="Blues",
            title=f"🧩 Topic Distribution — {competitor_type.capitalize()} Competitors"
        )

        fig.update_layout(
            height=600,
            margin=dict(t=50, l=25, r=25, b=25),
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a",
            font=dict(color="#f1f5f9")
        )

        st.plotly_chart(fig, use_container_width=True)






def show_topic_visualization(df=None, competitor_type=None, mode="light"):

        """Main function to display topic visualizations with filtering for competitor groups"""
        
        # ## Dynamic header
        # if competitor_type == "close":
        #     st.header("📊 Topic Analysis – Close Competitors")
        # elif competitor_type == "international":
        #     st.header("📊 Topic Analysis – International Competitors")
        # else:
        #     st.header("📊 Topic Analysis & Comparison")
        
        visualizer = TopicVisualizer()

        # Load filtered data
        if not visualizer.load_data(df=df, filter_type=competitor_type):
            return True

        # Display metrics
        # visualizer.display_metrics()
        # st.markdown("---")
        
        # Create tabs for different analysis views
        tabs = st.tabs([
            "📊 Competitive Analysis",
            "📊 Simple Topic Comparison", 
            "🎯 Priority Matrix"
        ])

        with tabs[0]:
            st.subheader("📊 Competitive Analysis - Topic Distribution")
            if not visualizer.competitor_data.empty:
                # Flatten topic lists safely
                website_topics = {}
                for site, rows in visualizer.competitor_data.groupby("website"):
                    all_topics = []
                    for t in rows["topics"]:
                        if isinstance(t, list):
                            all_topics.extend(t)
                        elif isinstance(t, str) and t.strip():
                            all_topics.extend([s.strip() for s in t.split(",")])
                    website_topics[site] = all_topics

                visualizer._create_competitor_topic_treemap(
                    website_topics,
                    competitor_type=competitor_type
                )
            else:
                st.info("No competitor data available for treemap.")
    

        with tabs[1]:
            st.subheader("📊 Simple Topic Comparison")
            visualizer.create_simple_topic_comparison(competitor_type=competitor_type)


        with tabs[2]:
            st.subheader("🎯 Priority Matrix - Topic Overlap Analysis")

            try:
                df_cache = get_cached_data()
                if not df_cache.empty:
                    # Use the correct competitor group parameter
                    competitor_group = "close" if competitor_type == "close" else "international"
                    fig = create_topic_sankey(df_cache, competitor_group=competitor_group, top_n=20)
                    st.plotly_chart(fig, use_container_width=True)

                else:
                    st.info("No cached data found — please scrape competitors first.")
            except Exception as e:
                st.error(f"Priority Matrix error: {e}")



        st.markdown("---")
        
        # Simple insights section
        # st.subheader("Summary")
        
        # if not visualizer.base_data.empty and not visualizer.competitor_data.empty:
        #     base_topics = visualizer.extract_topics(visualizer.base_data)
        #     competitor_topics = visualizer.extract_topics(visualizer.competitor_data)
            
        #     col1, col2, col3 = st.columns(3)
        #     with col1:
        #         st.metric("Your Topics", len(base_topics))
        #     with col2:
        #         st.metric("Competitor Topics", len(competitor_topics))
        #     with col3:
        #         common_topics = set(base_topics.keys()) & set(competitor_topics.keys())
        #         st.metric("Common Topics", len(common_topics))
            
        #     st.markdown("---")


def normalize_url(u):
    """Normalize URL for consistent matching across all functions"""
    if not isinstance(u, str):
        return ""
    return u.lower().replace("https://", "").replace("http://", "").replace("www.", "").strip('/')



def create_topic_network_old(df, competitor_group="close", top_n=20):
    """
    Build a COMPLETELY ACCURATE competitor–topic network graph.
    This version fixes all calculation and mapping issues.
    """

    # --- Step 1: Proper competitor filtering based on actual data ---
    print(f"DEBUG: Creating network for {competitor_group} competitors")
    
    # Get competitor sites from config
    competitor_sites = [s for s in SITES if s.get("type") == f"competitor_{competitor_group}"]
    competitor_urls = [normalize_url(s["url"]) for s in competitor_sites]
    competitor_names = {normalize_url(s["url"]): s.get("name", s["url"].split("//")[-1].split("/")[0]) for s in competitor_sites}
    
    print(f"DEBUG: Competitor URLs: {competitor_urls}")
    print(f"DEBUG: Competitor names: {competitor_names}")
    
    # Filter data to only include the selected competitor group
    df["website_clean"] = df["website"].apply(normalize_url)
    df_filtered = df[df["website_clean"].isin(competitor_urls)].copy()
    
    print(f"DEBUG: Filtered data shape: {df_filtered.shape}")
    print(f"DEBUG: Filtered websites: {df_filtered['website_clean'].unique()}")

    if df_filtered.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"No data available for {competitor_group.title()} competitors",
            template="plotly_dark", 
            height=500,
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a"
        )
        return fig

    # --- Step 2: Intelligent topic normalization and deduplication ---
    all_topics = []
    topic_website_map = {}  # website -> set of topics
    website_topic_counts = {}  # website -> topic -> count
    topic_normalization_map = {}  # original -> normalized
    
    print("DEBUG: Processing topics with intelligent normalization...")
    
    def normalize_topic(topic):
        """Intelligent topic normalization to handle duplicates, case, acronyms, and synonyms."""
        if not topic or not topic.strip():
            return None
            
        # Basic cleaning
        clean = topic.strip()
        
        # Handle common acronyms and synonyms
        acronym_map = {
            'ai': 'Artificial Intelligence',
            'artificial intelligence': 'Artificial Intelligence',
            'ux': 'User Experience',
            'ui': 'User Interface',
            'ui/ux': 'User Experience',
            'ux/ui': 'User Experience',
            'user experience': 'User Experience',
            'user interface': 'User Interface',
            'digital transformation': 'Digital Transformation',
            'digital engineering': 'Digital Engineering',
            'business strategy': 'Business Strategy',
            'cybersecurity': 'Cybersecurity',
            'cyber security': 'Cybersecurity',
            'cyber-security': 'Cybersecurity',
            'ai transformation': 'AI Transformation',
            'ai-transformation': 'AI Transformation',
            'scaling ai': 'AI Scaling',
            'scaling artificial intelligence': 'AI Scaling',
            'organizational readiness': 'Organizational Readiness',
            'career development': 'Career Development',
            'career opportunities': 'Career Opportunities',
            'operating model': 'Operating Model',
            'business model': 'Business Model',
            'innovation': 'Innovation',
            'consulting': 'Consulting',
            'sustainability': 'Sustainability',
            'technology': 'Technology',
            'engineering': 'Engineering',
            'design': 'Design',
            'strategy': 'Strategy',
            'transformation': 'Transformation',
            'reinvention': 'Reinvention',
            're-invention': 'Reinvention'
        }
        
        # Check for exact matches first (case-insensitive)
        lower_clean = clean.lower()
        for key, value in acronym_map.items():
            if lower_clean == key.lower():
                return value
        
        # Check for partial matches (contains)
        for key, value in acronym_map.items():
            if key.lower() in lower_clean or lower_clean in key.lower():
                return value
        
        # If no mapping found, return title case
        return clean.title()
    
    for _, row in df_filtered.iterrows():
        site = row["website_clean"]  # Use cleaned website
        topics_raw = row["topics"]
        
        # Parse topics correctly based on actual data format
        parsed_topics = []
        if isinstance(topics_raw, str) and topics_raw.strip():
            # Handle comma-separated string format (most common in your data)
            parsed_topics = [t.strip() for t in topics_raw.split(',') if t.strip()]
        elif isinstance(topics_raw, list):
            parsed_topics = [str(t).strip() for t in topics_raw if str(t).strip()]
        
        # Clean and normalize topics with intelligent deduplication
        for topic in parsed_topics:
            if topic and topic.strip():
                normalized_topic = normalize_topic(topic)
                if normalized_topic:
                    all_topics.append(normalized_topic)
                    
                    # Track topic-website relationships
                    if site not in topic_website_map:
                        topic_website_map[site] = set()
                        website_topic_counts[site] = Counter()
                    
                    topic_website_map[site].add(normalized_topic)
                    website_topic_counts[site][normalized_topic] += 1
                    
                    # Store original -> normalized mapping for debugging
                    topic_normalization_map[topic] = normalized_topic

    # Get top topics by overall frequency
    topic_counts = Counter(all_topics)
    top_topics = [t for t, _ in topic_counts.most_common(top_n)]
    
    print(f"DEBUG: Normalization examples:")
    for orig, norm in list(topic_normalization_map.items())[:10]:
        print(f"  '{orig}' -> '{norm}'")
    
    print(f"DEBUG: Top normalized topics: {top_topics[:10]}")
    print(f"DEBUG: Topic counts: {dict(topic_counts.most_common(10))}")
    print(f"DEBUG: Total unique topics after normalization: {len(topic_counts)}")

    # --- Step 3: Create accurate network graph ---
    G = nx.Graph()
    
    # Add competitor nodes with proper names
    for site in df_filtered["website_clean"].unique():
        display_name = competitor_names.get(site, site.split('.')[0])
        G.add_node(site, type="competitor", name=display_name, size=20)
        print(f"DEBUG: Added competitor node: {site} -> {display_name}")

    # Add topic nodes and create accurate edges
    for topic in top_topics:
        G.add_node(topic, type="topic", name=topic, size=15)
        
        # Create edges only for actual relationships
        for site, site_topics in topic_website_map.items():
            if topic in site_topics:
                G.add_edge(site, topic)
                print(f"DEBUG: Added edge: {site} -> {topic}")

    print(f"DEBUG: Graph nodes: {len(G.nodes())}")
    print(f"DEBUG: Graph edges: {len(G.edges())}")

    # --- Step 4: Calculate accurate node attributes ---
    degree = dict(G.degree())
    
    # Calculate proper node sizes based on actual relationships
    for node, data in G.nodes(data=True):
        if data["type"] == "competitor":
            # Size based on number of topics covered
            topic_count = len([n for n in G.neighbors(node) if G.nodes[n]["type"] == "topic"])
            G.nodes[node]["size"] = 25 + topic_count * 2
        else:
            # Size based on how many competitors mention this topic
            competitor_count = len([n for n in G.neighbors(node) if G.nodes[n]["type"] == "competitor"])
            G.nodes[node]["size"] = 15 + competitor_count * 3

    # --- Step 5: Create optimal layout ---
    if len(G.nodes()) > 1:
        # Use force-directed layout for better positioning
        pos = nx.spring_layout(G, k=3.0, iterations=300, seed=42)
    else:
        pos = {list(G.nodes())[0]: (0, 0)}

    # --- Step 6: Build accurate visualization ---
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    # Create edges
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(color="rgba(148,163,184,0.6)", width=1.5),
        hoverinfo="none"
    )

    # Create nodes with accurate information
    node_x, node_y, colors, sizes, labels, hover_texts = [], [], [], [], [], []
    
    for node, data in G.nodes(data=True):
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        sizes.append(data["size"])
        
        if data["type"] == "competitor":
            colors.append("#38bdf8")  # Blue for competitors
            display_name = data.get("name", node.split('.')[0])
            
            # Get actual topics this competitor covers
            connected_topics = [n for n in G.neighbors(node) if G.nodes[n]["type"] == "topic"]
            topic_frequency = website_topic_counts.get(node, Counter())
            
            hover_texts.append(
                f"<b>Competitor:</b> {display_name}<br>"
                f"<b>Topics Covered:</b> {len(connected_topics)}<br>"
                f"<b>Total Topic Mentions:</b> {sum(topic_frequency.values())}<br>"
                f"<b>Top Topics:</b> {', '.join([t for t, _ in topic_frequency.most_common(3)])}"
            )
            labels.append(display_name)
        else:
            colors.append("#c084fc")  # Purple for topics
            
            # Get competitors that mention this topic
            connected_competitors = [n for n in G.neighbors(node) if G.nodes[n]["type"] == "competitor"]
            competitor_names_list = [G.nodes[c].get("name", c.split('.')[0]) for c in connected_competitors]
            
            hover_texts.append(
                f"<b>Topic:</b> {node}<br>"
                f"<b>Mentioned by:</b> {len(connected_competitors)} competitors<br>"
                f"<b>Competitors:</b> {', '.join(competitor_names_list)}<br>"
                f"<b>Total Mentions:</b> {topic_counts[node]}"
            )
            labels.append(node)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=labels,
        hovertext=hover_texts,
        textposition="top center",
        hoverinfo="text",
        marker=dict(
            size=sizes,
            color=colors,
            line=dict(width=2, color="rgba(255,255,255,0.3)"),
            opacity=0.9
        )
    )

    # Create the final accurate figure
    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=f"Accurate Topic Relationship Network — {competitor_group.title()} Competitors",
        showlegend=False,
        hovermode="closest",
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        margin=dict(l=20, r=20, t=80, b=20),
        height=700,
        font=dict(size=12, color="#e2e8f0")
    )
    
    # Clean axis configuration
    fig.update_xaxes(showgrid=False, zeroline=False, visible=False, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(showgrid=False, zeroline=False, visible=False)

    print(f"DEBUG: Created accurate network with {len(G.nodes())} nodes and {len(G.edges())} edges")
    return fig

def create_topic_network_old_v2(df, competitor_group="close", top_n=20):
    """
    Build a COMPLETELY ACCURATE competitor–topic network graph with intelligent normalization.
    """
    
    print(f"DEBUG: Creating network for {competitor_group} competitors")
    
    # Get competitor sites from config
    competitor_sites = [s for s in SITES if s.get("type") == f"competitor_{competitor_group}"]
    competitor_urls = [normalize_url(s["url"]) for s in competitor_sites]
    competitor_names = {normalize_url(s["url"]): s.get("name", s["url"].split("//")[-1].split("/")[0]) for s in competitor_sites}
    
    print(f"DEBUG: Competitor URLs: {competitor_urls}")
    print(f"DEBUG: Competitor names: {competitor_names}")
    
    # Filter data to only include the selected competitor group
    df["website_clean"] = df["website"].apply(normalize_url)
    df_filtered = df[df["website_clean"].isin(competitor_urls)].copy()
    
    print(f"DEBUG: Filtered data shape: {df_filtered.shape}")
    print(f"DEBUG: Filtered websites: {df_filtered['website_clean'].unique()}")

    if df_filtered.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"No data available for {competitor_group.title()} competitors",
            template="plotly_dark", 
            height=500,
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a"
        )
        return fig

    def normalize_topic(topic):
        """Intelligent topic normalization to handle duplicates, case, acronyms, and synonyms."""
        if not topic or not topic.strip():
            return None
            
        # Basic cleaning
        clean = topic.strip()
        
        # Handle common acronyms and synonyms
        acronym_map = {
            'ai': 'Artificial Intelligence',
            'artificial intelligence': 'Artificial Intelligence',
            'ux': 'User Experience',
            'ui': 'User Interface',
            'ui/ux': 'User Experience',
            'ux/ui': 'User Experience',
            'user experience': 'User Experience',
            'user interface': 'User Interface',
            'digital transformation': 'Digital Transformation',
            'digital engineering': 'Digital Engineering',
            'business strategy': 'Business Strategy',
            'cybersecurity': 'Cybersecurity',
            'cyber security': 'Cybersecurity',
            'cyber-security': 'Cybersecurity',
            'ai transformation': 'AI Transformation',
            'ai-transformation': 'AI Transformation',
            'scaling ai': 'AI Scaling',
            'scaling artificial intelligence': 'AI Scaling',
            'organizational readiness': 'Organizational Readiness',
            'career development': 'Career Development',
            'career opportunities': 'Career Opportunities',
            'operating model': 'Operating Model',
            'business model': 'Business Model',
            'innovation': 'Innovation',
            'consulting': 'Consulting',
            'sustainability': 'Sustainability',
            'technology': 'Technology',
            'engineering': 'Engineering',
            'design': 'Design',
            'strategy': 'Strategy',
            'transformation': 'Transformation',
            'reinvention': 'Reinvention',
            're-invention': 'Reinvention'
        }
        
        # Check for exact matches first (case-insensitive)
        lower_clean = clean.lower()
        for key, value in acronym_map.items():
            if lower_clean == key.lower():
                return value
        
        # Check for partial matches (contains)
        for key, value in acronym_map.items():
            if key.lower() in lower_clean or lower_clean in key.lower():
                return value
        
        # If no mapping found, return title case
        return clean.title()

    # Process topics with intelligent normalization
    all_topics = []
    topic_website_map = {}  # website -> set of topics
    website_topic_counts = {}  # website -> topic -> count
    topic_normalization_map = {}  # original -> normalized
    
    print("DEBUG: Processing topics with intelligent normalization...")
    
    for _, row in df_filtered.iterrows():
        site = row["website_clean"]  # Use cleaned website
        topics_raw = row["topics"]
        
        # Parse topics correctly based on actual data format
        parsed_topics = []
        if isinstance(topics_raw, str) and topics_raw.strip():
            # Handle comma-separated string format (most common in your data)
            parsed_topics = [t.strip() for t in topics_raw.split(',') if t.strip()]
        elif isinstance(topics_raw, list):
            parsed_topics = [str(t).strip() for t in topics_raw if str(t).strip()]
        
        # Clean and normalize topics with intelligent deduplication
        for topic in parsed_topics:
            if topic and topic.strip():
                normalized_topic = normalize_topic(topic)
                if normalized_topic:
                    all_topics.append(normalized_topic)
                    
                    # Track topic-website relationships
                    if site not in topic_website_map:
                        topic_website_map[site] = set()
                        website_topic_counts[site] = Counter()
                    
                    topic_website_map[site].add(normalized_topic)
                    website_topic_counts[site][normalized_topic] += 1
                    
                    # Store original -> normalized mapping for debugging
                    topic_normalization_map[topic] = normalized_topic

    # Get top topics by overall frequency
    topic_counts = Counter(all_topics)
    top_topics = [t for t, _ in topic_counts.most_common(top_n)]
    
    print(f"DEBUG: Normalization examples:")
    for orig, norm in list(topic_normalization_map.items())[:10]:
        print(f"  '{orig}' -> '{norm}'")
    
    print(f"DEBUG: Top normalized topics: {top_topics[:10]}")
    print(f"DEBUG: Topic counts: {dict(topic_counts.most_common(10))}")
    print(f"DEBUG: Total unique topics after normalization: {len(topic_counts)}")

    # Create accurate network graph
    G = nx.Graph()
    
    # Add competitor nodes with proper names
    for site in df_filtered["website_clean"].unique():
        display_name = competitor_names.get(site, site.split('.')[0])
        G.add_node(site, type="competitor", name=display_name, size=20)
        print(f"DEBUG: Added competitor node: {site} -> {display_name}")

    # Add topic nodes and create accurate edges
    for topic in top_topics:
        G.add_node(topic, type="topic", name=topic, size=15)
        
        # Create edges only for actual relationships
        for site, site_topics in topic_website_map.items():
            if topic in site_topics:
                G.add_edge(site, topic)
                print(f"DEBUG: Added edge: {site} -> {topic}")

    print(f"DEBUG: Graph nodes: {len(G.nodes())}")
    print(f"DEBUG: Graph edges: {len(G.edges())}")

    # Calculate accurate node attributes
    degree = dict(G.degree())
    
    # Calculate proper node sizes based on actual relationships
    for node, data in G.nodes(data=True):
        if data["type"] == "competitor":
            # Size based on number of topics covered
            topic_count = len([n for n in G.neighbors(node) if G.nodes[n]["type"] == "topic"])
            G.nodes[node]["size"] = 25 + topic_count * 2
        else:
            # Size based on how many competitors mention this topic
            competitor_count = len([n for n in G.neighbors(node) if G.nodes[n]["type"] == "competitor"])
            G.nodes[node]["size"] = 15 + competitor_count * 3

    # Create optimal layout
    if len(G.nodes()) > 1:
        # Use force-directed layout for better positioning
        pos = nx.spring_layout(G, k=3.0, iterations=300, seed=42)
    else:
        pos = {list(G.nodes())[0]: (0, 0)}

    # Build accurate visualization
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    # Create edges
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(color="rgba(148,163,184,0.6)", width=1.5),
        hoverinfo="none"
    )

    # Create nodes with accurate information
    node_x, node_y, colors, sizes, labels, hover_texts = [], [], [], [], [], []
    
    for node, data in G.nodes(data=True):
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        sizes.append(data["size"])
        
        if data["type"] == "competitor":
            colors.append("#38bdf8")  # Blue for competitors
            display_name = data.get("name", node.split('.')[0])
            
            # Get actual topics this competitor covers
            connected_topics = [n for n in G.neighbors(node) if G.nodes[n]["type"] == "topic"]
            topic_frequency = website_topic_counts.get(node, Counter())
            
            hover_texts.append(
                f"<b>Competitor:</b> {display_name}<br>"
                f"<b>Topics Covered:</b> {len(connected_topics)}<br>"
                f"<b>Total Topic Mentions:</b> {sum(topic_frequency.values())}<br>"
                f"<b>Top Topics:</b> {', '.join([t for t, _ in topic_frequency.most_common(3)])}"
            )
            labels.append(display_name)
        else:
            colors.append("#c084fc")  # Purple for topics
            
            # Get competitors that mention this topic
            connected_competitors = [n for n in G.neighbors(node) if G.nodes[n]["type"] == "competitor"]
            competitor_names_list = [G.nodes[c].get("name", c.split('.')[0]) for c in connected_competitors]
            
            hover_texts.append(
                f"<b>Topic:</b> {node}<br>"
                f"<b>Mentioned by:</b> {len(connected_competitors)} competitors<br>"
                f"<b>Competitors:</b> {', '.join(competitor_names_list)}<br>"
                f"<b>Total Mentions:</b> {topic_counts[node]}"
            )
            labels.append(node)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=labels,
        hovertext=hover_texts,
        textposition="top center",
        hoverinfo="text",
        marker=dict(
            size=sizes,
            color=colors,
            line=dict(width=2, color="rgba(255,255,255,0.3)"),
            opacity=0.9
        )
    )

    # Create the final accurate figure
    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=f"Accurate Topic Relationship Network — {competitor_group.title()} Competitors (Normalized)",
        showlegend=False,
        hovermode="closest",
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        margin=dict(l=20, r=20, t=80, b=20),
        height=700,
        font=dict(size=12, color="#e2e8f0")
    )
    
    # Clean axis configuration
    fig.update_xaxes(showgrid=False, zeroline=False, visible=False, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(showgrid=False, zeroline=False, visible=False)

    print(f"DEBUG: Created accurate network with {len(G.nodes())} nodes and {len(G.edges())} edges")
    return fig

def create_topic_network_old_messy(df, competitor_group="close", top_n=20):
    """
    Build a COMPLETELY ACCURATE competitor–topic network graph with correct competitor filtering.
    """
    
    print(f"DEBUG: Creating network for {competitor_group} competitors")
    
    # Get competitor sites from config
    competitor_sites = [s for s in SITES if s.get("type") == f"competitor_{competitor_group}"]
    
    # Create flexible URL matching
    competitor_urls = []
    competitor_names = {}
    
    for site in competitor_sites:
        normalized_url = normalize_url(site["url"])
        competitor_urls.append(normalized_url)
        competitor_names[normalized_url] = site.get("name", site["url"].split("//")[-1].split("/")[0])
        
        # Also add base domain for better matching
        base_domain = normalized_url.split('/')[0]
        if base_domain not in competitor_urls:
            competitor_urls.append(base_domain)
            competitor_names[base_domain] = site.get("name", site["url"].split("//")[-1].split("/")[0])
    
    print(f"DEBUG: Competitor URLs: {competitor_urls}")
    print(f"DEBUG: Competitor names: {competitor_names}")
    
    # Filter data with flexible matching
    df["website_clean"] = df["website"].apply(normalize_url)
    
    # Try multiple matching strategies - collect ALL matches
    df_filtered = pd.DataFrame()
    for url in competitor_urls:
        # Exact match
        exact_match = df[df["website_clean"] == url]
        if not exact_match.empty:
            df_filtered = pd.concat([df_filtered, exact_match], ignore_index=True)
            
        # Partial match (contains) - only if no exact match
        elif df["website_clean"].str.contains(url, na=False).any():
            partial_match = df[df["website_clean"].str.contains(url, na=False)]
            df_filtered = pd.concat([df_filtered, partial_match], ignore_index=True)
            
        # Reverse partial match (url contains website_clean) - only if no other match
        elif df["website_clean"].apply(lambda x: url in x if pd.notna(x) else False).any():
            reverse_match = df[df["website_clean"].apply(lambda x: url in x if pd.notna(x) else False)]
            df_filtered = pd.concat([df_filtered, reverse_match], ignore_index=True)
    
    # Remove duplicates (handle unhashable types)
    if not df_filtered.empty:
        # Convert unhashable columns to strings for deduplication
        df_filtered = df_filtered.copy()
        for col in df_filtered.columns:
            if df_filtered[col].dtype == 'object':
                df_filtered[col] = df_filtered[col].astype(str)
        df_filtered = df_filtered.drop_duplicates()
    
    print(f"DEBUG: Filtered data shape: {df_filtered.shape}")
    print(f"DEBUG: Filtered websites: {df_filtered['website_clean'].unique()}")

    if df_filtered.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"No data available for {competitor_group.title()} competitors",
            template="plotly_dark", 
            height=500,
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a"
        )
        return fig

    def normalize_topic(topic):
        """Intelligent topic normalization to handle duplicates, case, acronyms, and synonyms."""
        if not topic or not topic.strip():
            return None
            
        # Basic cleaning
        clean = topic.strip()
        
        # Handle common acronyms and synonyms
        acronym_map = {
            'ai': 'Artificial Intelligence',
            'artificial intelligence': 'Artificial Intelligence',
            'ux': 'User Experience',
            'ui': 'User Interface',
            'ui/ux': 'User Experience',
            'ux/ui': 'User Experience',
            'user experience': 'User Experience',
            'user interface': 'User Interface',
            'digital transformation': 'Digital Transformation',
            'digital engineering': 'Digital Engineering',
            'business strategy': 'Business Strategy',
            'cybersecurity': 'Cybersecurity',
            'cyber security': 'Cybersecurity',
            'cyber-security': 'Cybersecurity',
            'ai transformation': 'AI Transformation',
            'ai-transformation': 'AI Transformation',
            'scaling ai': 'AI Scaling',
            'scaling artificial intelligence': 'AI Scaling',
            'organizational readiness': 'Organizational Readiness',
            'career development': 'Career Development',
            'career opportunities': 'Career Opportunities',
            'operating model': 'Operating Model',
            'business model': 'Business Model',
            'innovation': 'Innovation',
            'consulting': 'Consulting',
            'sustainability': 'Sustainability',
            'technology': 'Technology',
            'engineering': 'Engineering',
            'design': 'Design',
            'strategy': 'Strategy',
            'transformation': 'Transformation',
            'reinvention': 'Reinvention',
            're-invention': 'Reinvention'
        }
        
        # Check for exact matches first (case-insensitive)
        lower_clean = clean.lower()
        for key, value in acronym_map.items():
            if lower_clean == key.lower():
                return value
        
        # Check for partial matches (contains)
        for key, value in acronym_map.items():
            if key.lower() in lower_clean or lower_clean in key.lower():
                return value
        
        # If no mapping found, return title case
        return clean.title()

    # Process topics with intelligent normalization
    all_topics = []
    topic_website_map = {}  # website -> set of topics
    website_topic_counts = {}  # website -> topic -> count
    topic_normalization_map = {}  # original -> normalized
    
    print("DEBUG: Processing topics with intelligent normalization...")
    
    for _, row in df_filtered.iterrows():
        site = row["website_clean"]  # Use cleaned website
        topics_raw = row["topics"]
        
        # Parse topics correctly based on actual data format
        parsed_topics = []
        if isinstance(topics_raw, str) and topics_raw.strip():
            # Handle comma-separated string format (most common in your data)
            parsed_topics = [t.strip() for t in topics_raw.split(',') if t.strip()]
        elif isinstance(topics_raw, list):
            parsed_topics = [str(t).strip() for t in topics_raw if str(t).strip()]
        
        # Clean and normalize topics with intelligent deduplication
        for topic in parsed_topics:
            if topic and topic.strip():
                normalized_topic = normalize_topic(topic)
                if normalized_topic:
                    all_topics.append(normalized_topic)
                    
                    # Track topic-website relationships
                    if site not in topic_website_map:
                        topic_website_map[site] = set()
                        website_topic_counts[site] = Counter()
                    
                    topic_website_map[site].add(normalized_topic)
                    website_topic_counts[site][normalized_topic] += 1
                    
                    # Store original -> normalized mapping for debugging
                    topic_normalization_map[topic] = normalized_topic

    # Get top topics by overall frequency
    topic_counts = Counter(all_topics)
    top_topics = [t for t, _ in topic_counts.most_common(top_n)]
    
    print(f"DEBUG: Normalization examples:")
    for orig, norm in list(topic_normalization_map.items())[:10]:
        print(f"  '{orig}' -> '{norm}'")
    
    print(f"DEBUG: Top normalized topics: {top_topics[:10]}")
    print(f"DEBUG: Topic counts: {dict(topic_counts.most_common(10))}")
    print(f"DEBUG: Total unique topics after normalization: {len(topic_counts)}")

    # Create accurate network graph
    G = nx.Graph()
    
    # Add competitor nodes with proper names
    for site in df_filtered["website_clean"].unique():
        # Find the best matching name
        display_name = site
        for url, name in competitor_names.items():
            if url in site or site in url:
                display_name = name
                break
        
        G.add_node(site, type="competitor", name=display_name, size=20)
        print(f"DEBUG: Added competitor node: {site} -> {display_name}")

    # Add topic nodes and create accurate edges
    for topic in top_topics:
        G.add_node(topic, type="topic", name=topic, size=15)
        
        # Create edges only for actual relationships
        for site, site_topics in topic_website_map.items():
            if topic in site_topics:
                G.add_edge(site, topic)
                print(f"DEBUG: Added edge: {site} -> {topic}")

    print(f"DEBUG: Graph nodes: {len(G.nodes())}")
    print(f"DEBUG: Graph edges: {len(G.edges())}")

    # Calculate accurate node attributes
    degree = dict(G.degree())
    
    # Calculate proper node sizes based on actual relationships
    for node, data in G.nodes(data=True):
        if data["type"] == "competitor":
            # Size based on number of topics covered
            topic_count = len([n for n in G.neighbors(node) if G.nodes[n]["type"] == "topic"])
            G.nodes[node]["size"] = 25 + topic_count * 2
        else:
            # Size based on how many competitors mention this topic
            competitor_count = len([n for n in G.neighbors(node) if G.nodes[n]["type"] == "competitor"])
            G.nodes[node]["size"] = 15 + competitor_count * 3

    # Create optimal layout
    if len(G.nodes()) > 1:
        # Use force-directed layout for better positioning
        pos = nx.spring_layout(G, k=3.0, iterations=300, seed=42)
    else:
        pos = {list(G.nodes())[0]: (0, 0)}

    # Build accurate visualization
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    # Create edges
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(color="rgba(148,163,184,0.6)", width=1.5),
        hoverinfo="none"
    )

    # Create nodes with accurate information
    node_x, node_y, colors, sizes, labels, hover_texts = [], [], [], [], [], []
    
    for node, data in G.nodes(data=True):
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        sizes.append(data["size"])
        
        if data["type"] == "competitor":
            colors.append("#38bdf8")  # Blue for competitors
            display_name = data.get("name", node.split('.')[0])
            
            # Get actual topics this competitor covers
            connected_topics = [n for n in G.neighbors(node) if G.nodes[n]["type"] == "topic"]
            topic_frequency = website_topic_counts.get(node, Counter())
            
            hover_texts.append(
                f"<b>Competitor:</b> {display_name}<br>"
                f"<b>Topics Covered:</b> {len(connected_topics)}<br>"
                f"<b>Total Topic Mentions:</b> {sum(topic_frequency.values())}<br>"
                f"<b>Top Topics:</b> {', '.join([t for t, _ in topic_frequency.most_common(3)])}"
            )
            labels.append(display_name)
        else:
            colors.append("#c084fc")  # Purple for topics
            
            # Get competitors that mention this topic
            connected_competitors = [n for n in G.neighbors(node) if G.nodes[n]["type"] == "competitor"]
            competitor_names_list = [G.nodes[c].get("name", c.split('.')[0]) for c in connected_competitors]
            
            hover_texts.append(
                f"<b>Topic:</b> {node}<br>"
                f"<b>Mentioned by:</b> {len(connected_competitors)} competitors<br>"
                f"<b>Competitors:</b> {', '.join(competitor_names_list)}<br>"
                f"<b>Total Mentions:</b> {topic_counts[node]}"
            )
            labels.append(node)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=labels,
        hovertext=hover_texts,
        textposition="top center",
        hoverinfo="text",
        marker=dict(
            size=sizes,
            color=colors,
            line=dict(width=2, color="rgba(255,255,255,0.3)"),
            opacity=0.9
        )
    )

    # Create the final accurate figure
    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=f"Accurate Topic Relationship Network — {competitor_group.title()} Competitors (All {len(df_filtered['website_clean'].unique())} Competitors)",
        showlegend=False,
        hovermode="closest",
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        margin=dict(l=20, r=20, t=80, b=20),
        height=700,
        font=dict(size=12, color="#e2e8f0")
    )
    
    # Clean axis configuration
    fig.update_xaxes(showgrid=False, zeroline=False, visible=False, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(showgrid=False, zeroline=False, visible=False)

    print(f"DEBUG: Created accurate network with {len(G.nodes())} nodes and {len(G.edges())} edges")
    return fig

def create_topic_network(df, competitor_group="close", max_topics=25):
    """
    Build a FIXED competitor–topic network graph with proper logic and calculations.
    """
    
    print(f"DEBUG: Creating FIXED network for {competitor_group} competitors")
    
    # Get competitor sites from config
    competitor_sites = [s for s in SITES if s.get("type") == f"competitor_{competitor_group}"]
    
    if not competitor_sites:
        print(f"DEBUG: No competitors found for group: {competitor_group}")
        fig = go.Figure()
        fig.update_layout(
            title=f"No competitors configured for {competitor_group.title()} group",
            template="plotly_dark", 
            height=500,
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a"
        )
        return fig
    
    # Create competitor URL matching with multiple strategies
    competitor_urls = []
    competitor_names = {}
    
    for site in competitor_sites:
        url = site["url"]
        name = site.get("name", url.split("//")[-1].split("/")[0])
        
        # Add multiple URL variations for better matching
        normalized_url = normalize_url(url)
        competitor_urls.append(normalized_url)
        competitor_names[normalized_url] = name
        
        # Add base domain
        base_domain = normalized_url.split('/')[0]
        if base_domain not in competitor_urls:
            competitor_urls.append(base_domain)
            competitor_names[base_domain] = name
        
        # Add original URL variations
        if url not in competitor_urls:
            competitor_urls.append(url)
            competitor_names[url] = name
    
    print(f"DEBUG: Competitor URLs: {competitor_urls}")
    print(f"DEBUG: Competitor names: {competitor_names}")
    
    # Special debugging for International Competitors
    if competitor_group == "international":
        print(f"DEBUG: INTERNATIONAL COMPETITORS ANALYSIS:")
        print(f"DEBUG: Expected 8 international competitors:")
        for i, site in enumerate(competitor_sites, 1):
            print(f"  {i}. {site['name']} - {site['url']}")
        print(f"DEBUG: Total competitor sites found: {len(competitor_sites)}")
    
    # Filter data with improved matching - use same logic as Sankey function
    df["website_clean"] = df["website"].apply(normalize_url)
    
    # Use consistent matching logic
    matched_rows = []
    matched_sites = set()
    
    for _, row in df.iterrows():
        site_url = row["website"]
        normalized_site = normalize_url(site_url)
        
        # Check if this site matches any competitor with improved matching
        for i, comp_url in enumerate(competitor_urls):
            norm_comp_url = normalize_url(comp_url)
            match_found = False
            
            # Exact match
            if normalized_site == norm_comp_url:
                match_found = True
                print(f"DEBUG: Exact match: {site_url} -> {comp_url}")
            
            # Partial match - competitor URL in site URL
            elif norm_comp_url in normalized_site and len(norm_comp_url) > 3:
                match_found = True
                print(f"DEBUG: Partial match (comp in site): {site_url} -> {comp_url}")
            
            # Reverse match - site URL in competitor URL
            elif normalized_site in norm_comp_url and len(normalized_site) > 3:
                match_found = True
                print(f"DEBUG: Reverse match (site in comp): {site_url} -> {comp_url}")
            
            # Domain match - check if domains match
            elif ('.' in normalized_site and '.' in norm_comp_url):
                site_domain = '.'.join(normalized_site.split('.')[-2:])
                comp_domain = '.'.join(norm_comp_url.split('.')[-2:])
                if site_domain == comp_domain:
                    match_found = True
                    print(f"DEBUG: Domain match: {site_url} -> {comp_url}")
            
            if match_found and site_url not in matched_sites:
                matched_rows.append(row)
                matched_sites.add(site_url)
                break
    
    # Create filtered dataframe efficiently
    if matched_rows:
        df_filtered = pd.DataFrame(matched_rows)
    else:
        df_filtered = pd.DataFrame()
    
    # Remove duplicates properly
    if not df_filtered.empty:
        # Create a hashable version for deduplication
        df_filtered = df_filtered.copy()
        # Convert problematic columns to strings for deduplication
        for col in df_filtered.columns:
            if df_filtered[col].dtype == 'object':
                df_filtered[col] = df_filtered[col].astype(str)
        
        # Remove duplicates based on all columns
        df_filtered = df_filtered.drop_duplicates()
    
    print(f"DEBUG: Filtered data shape: {df_filtered.shape}")
    print(f"DEBUG: Filtered websites: {df_filtered['website_clean'].unique()}")
    print(f"DEBUG: All available websites in data: {df['website'].unique()}")
    print(f"DEBUG: Total rows in original data: {len(df)}")
    print(f"DEBUG: Looking for {len(competitor_urls)} competitors: {competitor_urls}")
    
    # Special analysis for International Competitors
    if competitor_group == "international":
        print(f"DEBUG: INTERNATIONAL MATCHING RESULTS:")
        print(f"DEBUG: Found {len(matched_sites)} international competitors in data:")
        for site in matched_sites:
            print(f"  ✓ {site}")
        
        missing_international = []
        for comp_url in competitor_urls:
            found = False
            for matched_site in matched_sites:
                if normalize_url(comp_url) in normalize_url(matched_site) or normalize_url(matched_site) in normalize_url(comp_url):
                    found = True
                    break
            if not found:
                missing_international.append(comp_url)
        
        if missing_international:
            print(f"DEBUG: Missing international competitors ({len(missing_international)}):")
            for url in missing_international:
                name = competitor_names.get(url, url.split("//")[-1].split("/")[0])
                print(f"  ✗ {name} - {url}")
        else:
            print(f"DEBUG: ✓ All 8 international competitors found!")
    
    # Additional debugging: show what we're trying to match
    print(f"DEBUG: Available websites in data (normalized):")
    for website in df['website'].unique():
        normalized = normalize_url(website)
        print(f"  '{website}' -> '{normalized}'")
    
    if df_filtered.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"No data available for {competitor_group.title()} competitors",
            template="plotly_dark", 
            height=500,
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a"
        )
        return fig
    
    def normalize_topic(topic):
        """Intelligent topic normalization to handle duplicates, case, acronyms, and synonyms."""
        if not topic or not topic.strip():
            return None
            
        # Basic cleaning - remove brackets, quotes, and extra whitespace
        clean = topic.strip().strip("[]'\"")
        
        # Handle common acronyms and synonyms with case-insensitive matching
        acronym_map = {
            'ai': 'Artificial Intelligence',
            'artificial intelligence': 'Artificial Intelligence',
            'ux': 'User Experience',
            'ui': 'User Interface',
            'ui/ux': 'User Experience',
            'ux/ui': 'User Experience',
            'user experience': 'User Experience',
            'user interface': 'User Interface',
            'digital transformation': 'Digital Transformation',
            'digital engineering': 'Digital Engineering',
            'business strategy': 'Business Strategy',
            'cybersecurity': 'Cybersecurity',
            'cyber security': 'Cybersecurity',
            'cyber-security': 'Cybersecurity',
            'ai transformation': 'AI Transformation',
            'ai-transformation': 'AI Transformation',
            'scaling ai': 'AI Scaling',
            'scaling artificial intelligence': 'AI Scaling',
            'organizational readiness': 'Organizational Readiness',
            'career development': 'Career Development',
            'career opportunities': 'Career Opportunities',
            'operating model': 'Operating Model',
            'business model': 'Business Model',
            'innovation': 'Innovation',
            'consulting': 'Consulting',
            'sustainability': 'Sustainability',
            'technology': 'Technology',
            'engineering': 'Engineering',
            'design': 'Design',
            'strategy': 'Strategy',
            'transformation': 'Transformation',
            'reinvention': 'Reinvention',
            're-invention': 'Reinvention',
            'machine learning': 'Machine Learning',
            'ml': 'Machine Learning',
            'data science': 'Data Science',
            'cloud computing': 'Cloud Computing',
            'iot': 'Internet of Things',
            'internet of things': 'Internet of Things',
            'blockchain': 'Blockchain',
            'automation': 'Automation',
            'robotics': 'Robotics',
            'virtual reality': 'Virtual Reality',
            'vr': 'Virtual Reality',
            'augmented reality': 'Augmented Reality',
            'ar': 'Augmented Reality'
        }
        
        # Normalize to lowercase for comparison
        lower_clean = clean.lower().strip()
        
        # Check for exact matches first (case-insensitive)
        for key, value in acronym_map.items():
            if lower_clean == key.lower():
                return value
        
        # Check for partial matches (contains) - but be more strict to avoid false positives
        for key, value in acronym_map.items():
            key_lower = key.lower()
            if (key_lower in lower_clean and len(key_lower) > 3) or (lower_clean in key_lower and len(lower_clean) > 3):
                return value
        
        # If no mapping found, return properly capitalized version
        # Handle special cases for consistent capitalization
        if lower_clean in ['innovation', 'business strategy', 'cybersecurity']:
            return clean.title()
        
        # For other topics, use title case but preserve acronyms
        words = clean.split()
        result = []
        for word in words:
            if len(word) <= 3 and word.isupper():
                result.append(word)  # Keep acronyms as-is
            else:
                result.append(word.title())
        return ' '.join(result)

    def parse_topics_safely(topics_raw):
        """Safely parse topics from various data formats."""
        if not topics_raw or pd.isna(topics_raw):
            return []
        
        # Handle string format
        if isinstance(topics_raw, str):
            topics_str = topics_raw.strip()
            if not topics_str or topics_str in ['[]', 'null', 'none', '']:
                return []
            
            # Try to parse as list first
            try:
                parsed = ast.literal_eval(topics_str)
                if isinstance(parsed, list):
                    return [str(t).strip() for t in parsed if t and str(t).strip()]
            except:
                pass
            
            # Fallback to comma-separated
            return [t.strip() for t in topics_str.split(',') if t.strip()]
        
        # Handle list format
        elif isinstance(topics_raw, list):
            return [str(t).strip() for t in topics_raw if t and str(t).strip()]
        
        return []

    # Process topics with improved logic
    all_topics = []
    topic_website_map = {}  # website -> set of topics
    website_topic_counts = {}  # website -> topic -> count
    topic_normalization_map = {}  # original -> normalized
    
    print("DEBUG: Processing topics with improved logic...")
    
    for _, row in df_filtered.iterrows():
        site = row["website_clean"]
        topics_raw = row["topics"]
        
        # Parse topics safely
        parsed_topics = parse_topics_safely(topics_raw)
        
        # Process each topic
        for topic in parsed_topics:
            if topic and len(topic.strip()) > 2:  # Minimum length filter
                normalized_topic = normalize_topic(topic)
                if normalized_topic and len(normalized_topic.strip()) > 2:
                    all_topics.append(normalized_topic)
                    
                    # Track relationships
                    if site not in topic_website_map:
                        topic_website_map[site] = set()
                        website_topic_counts[site] = Counter()
                    
                    topic_website_map[site].add(normalized_topic)
                    website_topic_counts[site][normalized_topic] += 1
                    
                    # Store mapping for debugging
                    topic_normalization_map[topic] = normalized_topic
    
    # Get ALL topics - NO ARTIFICIAL FILTERING
    topic_counts = Counter(all_topics)
    
    # Only filter out topics with 0 mentions (shouldn't happen but safety check)
    all_meaningful_topics = {topic: count for topic, count in topic_counts.items() if count > 0}
    
    # Get top topics - NO FREQUENCY LIMITING, just limit by max_topics for visualization
    top_topics = [t for t, _ in Counter(all_meaningful_topics).most_common(max_topics)]
    
    print(f"DEBUG: Normalization examples:")
    for orig, norm in list(topic_normalization_map.items())[:10]:
        print(f"  '{orig}' -> '{norm}'")
    
    print(f"DEBUG: ALL topics found: {len(topic_counts)}")
    print(f"DEBUG: Meaningful topics: {len(all_meaningful_topics)}")
    print(f"DEBUG: Selected topics for visualization: {len(top_topics)}")
    print(f"DEBUG: Top topics: {top_topics}")
    print(f"DEBUG: Topic counts: {dict(topic_counts.most_common(15))}")
    print(f"DEBUG: Topic-Website mapping keys: {list(topic_website_map.keys())}")
    
    if not top_topics:
        fig = go.Figure()
        fig.update_layout(
            title=f"No meaningful topics found for {competitor_group.title()} competitors",
            template="plotly_dark", 
            height=500,
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a"
        )
        return fig
    
    # Create network graph
    G = nx.Graph()
    
    # Add competitor nodes
    for site in df_filtered["website_clean"].unique():
        # Find best matching name
        display_name = site
        for url, name in competitor_names.items():
            if url in site or site in url:
                display_name = name
                break
        
        G.add_node(site, type="competitor", name=display_name, size=30)
        print(f"DEBUG: Added competitor node: {site} -> {display_name}")
    
    # Add topic nodes first
    for topic in top_topics:
        G.add_node(topic, type="topic", name=topic, size=20)
    
    # Create edges for actual relationships - FIXED LOGIC
    for site, site_topics in topic_website_map.items():
        # Only create edges if the site exists in the graph
        if site in G.nodes():
            for topic in site_topics:
                if topic in G.nodes():
                    G.add_edge(site, topic)
                    print(f"DEBUG: Added edge: {site} -> {topic}")
    
    print(f"DEBUG: Graph nodes: {len(G.nodes())}")
    print(f"DEBUG: Graph edges: {len(G.edges())}")
    
    # Calculate node attributes properly - FIXED LOGIC
    for node, data in G.nodes(data=True):
        if data["type"] == "competitor":
            # Size based on actual topics from data, not graph structure
            site_topics = topic_website_map.get(node, set())
            topic_count = len(site_topics)
            G.nodes[node]["size"] = max(30, 30 + topic_count * 5)
        else:
            # Size based on actual competitors from data, not graph structure
            competitor_count = 0
            for site, site_topics in topic_website_map.items():
                if node in site_topics:
                    competitor_count += 1
            G.nodes[node]["size"] = max(20, 20 + competitor_count * 5)
    
    # Create optimal layout
    if len(G.nodes()) > 1:
        # Use spring layout with better parameters
        pos = nx.spring_layout(G, k=4.0, iterations=1000, seed=42)
    else:
        pos = {list(G.nodes())[0]: (0, 0)}
    
    # Build visualization
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
    
    # Create edges
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(color="rgba(148,163,184,0.6)", width=2),
        hoverinfo="none"
    )
    
    # Create nodes
    node_x, node_y, colors, sizes, labels, hover_texts = [], [], [], [], [], []
    
    for node, data in G.nodes(data=True):
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        sizes.append(data["size"])
        
        if data["type"] == "competitor":
            colors.append("#3b82f6")  # Blue for competitors
            display_name = data.get("name", node.split('.')[0])
            
            # Get connected topics
            connected_topics = [n for n in G.neighbors(node) if G.nodes[n]["type"] == "topic"]
            topic_frequency = website_topic_counts.get(node, Counter())
            
            hover_texts.append(
                f"<b>🏢 {display_name}</b><br>"
                f"<b>Topics Covered:</b> {len(connected_topics)}<br>"
                f"<b>Total Mentions:</b> {sum(topic_frequency.values())}<br>"
                f"<b>Top Topics:</b> {', '.join([t for t, _ in topic_frequency.most_common(3)])}"
            )
            labels.append(display_name)
        else:
            colors.append("#8b5cf6")  # Purple for topics
            
            # Get connected competitors
            connected_competitors = [n for n in G.neighbors(node) if G.nodes[n]["type"] == "competitor"]
            competitor_names_list = [G.nodes[c].get("name", c.split('.')[0]) for c in connected_competitors]
            
            hover_texts.append(
                f"<b>📊 {node}</b><br>"
                f"<b>Mentioned by:</b> {len(connected_competitors)} competitors<br>"
                f"<b>Competitors:</b> {', '.join(competitor_names_list)}<br>"
                f"<b>Total Mentions:</b> {topic_counts[node]}"
            )
            labels.append(node)
    
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=labels,
        hovertext=hover_texts,
        textposition="top center",
        hoverinfo="text",
        marker=dict(
            size=sizes,
            color=colors,
            line=dict(width=2, color="rgba(255,255,255,0.8)"),
            opacity=0.9
        ),
        textfont=dict(size=11, color="white", family="Arial")
    )
    
    # Create final figure
    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=f"🎯 Ultra Clean Topic Network — {competitor_group.title()} Competitors ({len(df_filtered['website_clean'].unique())} Competitors, {len(top_topics)} Topics)",
        showlegend=False,
        hovermode="closest",
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        margin=dict(l=50, r=50, t=120, b=50),
        height=800,  # Taller for better visibility
        font=dict(size=13, color="#e2e8f0")
    )
    
    # Clean axis configuration
    fig.update_xaxes(showgrid=False, zeroline=False, visible=False, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(showgrid=False, zeroline=False, visible=False)
    
    print(f"DEBUG: Created FIXED network with {len(G.nodes())} nodes and {len(G.edges())} edges")
    return fig

def create_topic_sankey(df, competitor_group="close", top_n=20):
    """
    Create a CLEAN Sankey diagram showing how competitors connect to shared topics.
    Fixed to reduce visual clutter and improve readability.
    """
    # --- FIRST: Filter data by competitor group ---
    print(f"DEBUG: ===== PRIORITY MATRIX DEBUGGING =====")
    print(f"DEBUG: Filtering for {competitor_group} competitors")
    print(f"DEBUG: Input data shape: {df.shape}")
    print(f"DEBUG: Input data columns: {df.columns.tolist()}")
    
    # Show sample of the data for debugging
    if not df.empty:
        print(f"DEBUG: Sample data (first 3 rows):")
        for i, (_, row) in enumerate(df.head(3).iterrows()):
            print(f"  Row {i+1}: website='{row.get('website', 'N/A')}', topics='{row.get('topics', 'N/A')}'")
        
        # Show ALL unique websites in the data
        print(f"DEBUG: ALL UNIQUE WEBSITES IN DATA:")
        unique_websites = df['website'].unique()
        for i, website in enumerate(unique_websites, 1):
            print(f"  {i}. '{website}'")
        print(f"DEBUG: Total unique websites: {len(unique_websites)}")
    
    # Check if 'website' column exists and has data
    if 'website' not in df.columns:
        print(f"DEBUG: ERROR - 'website' column not found in data!")
        print(f"DEBUG: Available columns: {df.columns.tolist()}")
        return go.Figure()
    
    if df['website'].isna().all():
        print(f"DEBUG: ERROR - All website values are NaN!")
        return go.Figure()
    
    # Get competitor sites from config based on group
    competitor_sites = [s for s in SITES if s.get("type") == f"competitor_{competitor_group}"]
    competitor_urls = [s["url"] for s in competitor_sites]
    competitor_names = {s["url"]: s.get("name", s["url"].split("//")[-1].split("/")[0]) for s in competitor_sites}
    
    print(f"DEBUG: {competitor_group} competitor URLs: {competitor_urls}")
    print(f"DEBUG: {competitor_group} competitor names: {competitor_names}")
    
    # Special debugging for International Competitors
    if competitor_group == "international":
        print(f"DEBUG: INTERNATIONAL COMPETITORS ANALYSIS:")
        print(f"DEBUG: Expected 8 international competitors:")
        for i, site in enumerate(competitor_sites, 1):
            print(f"  {i}. {site['name']} - {site['url']}")
        print(f"DEBUG: Total competitor sites found: {len(competitor_sites)}")
    
    # Use consistent URL matching like other functions
    # Create normalized competitor URLs for matching
    normalized_competitor_urls = [normalize_url(url) for url in competitor_urls]
    competitor_url_map = {normalize_url(url): url for url in competitor_urls}
    
    print(f"DEBUG: Normalized competitor URLs: {normalized_competitor_urls}")
    
    # Filter dataframe with flexible matching - more efficient approach
    matched_rows = []
    matched_sites = set()
    
    print(f"DEBUG: Starting matching process...")
    print(f"DEBUG: Will check {len(df)} rows against {len(competitor_urls)} competitor URLs")
    
    for row_idx, (_, row) in enumerate(df.iterrows()):
        site_url = row["website"]
        normalized_site = normalize_url(site_url)
        
        if row_idx < 5:  # Debug first 5 rows
            print(f"DEBUG: Row {row_idx+1}: Checking '{site_url}' -> '{normalized_site}'")
        
        # Check if this site matches any competitor with improved matching
        for i, norm_comp_url in enumerate(normalized_competitor_urls):
            # More flexible matching logic
            match_found = False
            
            # Exact match
            if normalized_site == norm_comp_url:
                match_found = True
                print(f"DEBUG: Exact match: {site_url} -> {competitor_urls[i]}")
            
            # Partial match - competitor URL in site URL
            elif norm_comp_url in normalized_site and len(norm_comp_url) > 3:
                match_found = True
                print(f"DEBUG: Partial match (comp in site): {site_url} -> {competitor_urls[i]}")
            
            # Reverse match - site URL in competitor URL
            elif normalized_site in norm_comp_url and len(normalized_site) > 3:
                match_found = True
                print(f"DEBUG: Reverse match (site in comp): {site_url} -> {competitor_urls[i]}")
            
            # Domain match - check if domains match (more precise)
            elif ('.' in normalized_site and '.' in norm_comp_url):
                site_domain = '.'.join(normalized_site.split('.')[-2:])  # Get last two parts (domain.tld)
                comp_domain = '.'.join(norm_comp_url.split('.')[-2:])    # Get last two parts (domain.tld)
                if site_domain == comp_domain:
                    match_found = True
                    print(f"DEBUG: Domain match: {site_url} -> {competitor_urls[i]}")
            
            if match_found and site_url not in matched_sites:
                matched_rows.append(row)
                matched_sites.add(site_url)
                print(f"DEBUG: ✓ ADDED TO MATCHED: {site_url}")
                break
            elif match_found and site_url in matched_sites:
                print(f"DEBUG: ⚠️ ALREADY MATCHED: {site_url}")
                break
    
    # Create filtered dataframe efficiently
    if matched_rows:
        df_filtered = pd.DataFrame(matched_rows)
        print(f"DEBUG: Successfully created filtered DataFrame with {len(matched_rows)} rows")
    else:
        df_filtered = pd.DataFrame()
        print(f"DEBUG: WARNING - No matched rows found! This will cause empty visualization.")
    
    print(f"DEBUG: ===== MATCHING SUMMARY =====")
    print(f"DEBUG: Total rows processed: {len(df)}")
    print(f"DEBUG: Matched sites found: {len(matched_sites)}")
    print(f"DEBUG: Matched sites: {list(matched_sites)}")
    print(f"DEBUG: Filtered data shape: {df_filtered.shape}")
    print(f"DEBUG: Filtered websites: {df_filtered['website'].unique()}")
    print(f"DEBUG: All available websites in data: {df['website'].unique()}")
    print(f"DEBUG: Looking for {len(competitor_urls)} competitors: {competitor_urls}")
    print(f"DEBUG: Normalized competitor URLs: {normalized_competitor_urls}")
    
    # Special analysis for International Competitors
    if competitor_group == "international":
        print(f"DEBUG: ===== INTERNATIONAL COMPETITORS DETAILED ANALYSIS =====")
        print(f"DEBUG: INTERNATIONAL MATCHING RESULTS:")
        print(f"DEBUG: Found {len(matched_sites)} international competitors in data:")
        for site in matched_sites:
            print(f"  ✓ {site}")
        
        print(f"DEBUG: All websites in original data:")
        for website in df['website'].unique():
            print(f"  - {website}")
        
        print(f"DEBUG: Matching analysis for each competitor:")
        missing_international = []
        for comp_url in competitor_urls:
            comp_name = competitor_names.get(comp_url, comp_url.split("//")[-1].split("/")[0])
            print(f"DEBUG: Checking {comp_name} ({comp_url})...")
            
            found = False
            norm_comp_url = normalize_url(comp_url)
            print(f"DEBUG:   Normalized competitor URL: '{norm_comp_url}'")
            
            for website in df['website'].unique():
                normalized_site = normalize_url(website)
                print(f"DEBUG:   Checking against '{website}' -> '{normalized_site}'")
                
                # Check all matching conditions
                if normalized_site == norm_comp_url:
                    print(f"DEBUG:     ✓ EXACT MATCH!")
                    found = True
                elif norm_comp_url in normalized_site and len(norm_comp_url) > 3:
                    print(f"DEBUG:     ✓ PARTIAL MATCH (comp in site)")
                    found = True
                elif normalized_site in norm_comp_url and len(normalized_site) > 3:
                    print(f"DEBUG:     ✓ REVERSE MATCH (site in comp)")
                    found = True
                elif ('.' in normalized_site and '.' in norm_comp_url):
                    site_domain = '.'.join(normalized_site.split('.')[-2:])
                    comp_domain = '.'.join(norm_comp_url.split('.')[-2:])
                    if site_domain == comp_domain:
                        print(f"DEBUG:     ✓ DOMAIN MATCH ({site_domain} == {comp_domain})")
                        found = True
                
                if found:
                    break
            
            if not found:
                missing_international.append(comp_url)
                print(f"DEBUG:   ✗ NO MATCH FOUND")
            else:
                print(f"DEBUG:   ✓ MATCH FOUND")
        
        if missing_international:
            print(f"DEBUG: Missing international competitors ({len(missing_international)}):")
            for url in missing_international:
                name = competitor_names.get(url, url.split("//")[-1].split("/")[0])
                print(f"  ✗ {name} - {url}")
        else:
            print(f"DEBUG: ✓ All 8 international competitors found!")
    
    # Additional debugging: show what we're trying to match
    print(f"DEBUG: Available websites in data (normalized):")
    for website in df['website'].unique():
        normalized = normalize_url(website)
        print(f"  '{website}' -> '{normalized}'")
    
    if df_filtered.empty:
        # Create a more informative error message
        missing_competitors = []
        for comp_url in competitor_urls:
            found = False
            norm_comp_url = normalize_url(comp_url)
            for website in df['website'].unique():
                normalized_site = normalize_url(website)
                
                # Use the same matching logic as the main function
                if (normalized_site == norm_comp_url or
                    (norm_comp_url in normalized_site and len(norm_comp_url) > 3) or
                    (normalized_site in norm_comp_url and len(normalized_site) > 3) or
                    ('.' in normalized_site and '.' in norm_comp_url and 
                     '.'.join(normalized_site.split('.')[-2:]) == '.'.join(norm_comp_url.split('.')[-2:]))):
                    found = True
                    break
            if not found:
                missing_competitors.append(comp_url)
        
        fig = go.Figure()
        fig.update_layout(
            title=f"No data available for {competitor_group.title()} Competitors",
            template="plotly_dark",
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a",
            height=500,
            annotations=[
                dict(
                    x=0.5, y=0.5,
                    xref="paper", yref="paper",
                    text=f"Missing competitors: {missing_competitors}<br>Please scrape these competitors first.",
                    showarrow=False,
                    font=dict(size=14, color="#e2e8f0")
                )
            ]
        )
        return fig
    
    # --- Normalize topics with improved deduplication ---
    all_rows = []
    topic_normalization_map = {}
    
    def normalize_topic_for_sankey(topic):
        """Normalize topics to prevent duplicates"""
        if not topic or not topic.strip():
            return None
        clean = topic.strip().strip("[]'\"")
        lower_clean = clean.lower()
        
        # Handle common duplicates
        if lower_clean in ['innovation', 'business strategy', 'cybersecurity']:
            return clean.title()
        return clean.title()
    
    # Process ONLY the filtered data
    for _, row in df_filtered.iterrows():
        site = row["website"]
        topics = row.get("topics", [])
        if isinstance(topics, str):
            try:
                topics = ast.literal_eval(topics)
            except Exception:
                topics = [t.strip() for t in topics.split(",")]
        topics = [t.strip() for t in topics if t.strip()]
        
        for t in topics:
            normalized_topic = normalize_topic_for_sankey(t)
            if normalized_topic:
                all_rows.append({"website": site, "topic": normalized_topic})

    df_long = pd.DataFrame(all_rows)
    
    # Get top topics with better filtering
    topic_counts = Counter(df_long["topic"])
    # Filter out topics with very low frequency to reduce clutter
    min_frequency = max(1, len(df_long) // 50)  # Dynamic minimum frequency
    meaningful_topics = {t: c for t, c in topic_counts.items() if c >= min_frequency}
    
    # Get top N meaningful topics
    top_topics = [t for t, _ in Counter(meaningful_topics).most_common(top_n)]
    df_long = df_long[df_long["topic"].isin(top_topics)]

    if df_long.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"No meaningful topics found for {competitor_group.capitalize()} Competitors",
            template="plotly_dark",
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a",
            height=500
        )
        return fig

    # --- Build Sankey nodes and links with improved structure ---
    competitors = df_long["website"].unique().tolist()
    topics = df_long["topic"].unique().tolist()
    
    # Create competitor name mapping function
    def get_competitor_name(website_url):
        """Get proper competitor name for a website URL"""
        normalized_comp = normalize_url(website_url)
        
        for norm_url, orig_url in competitor_url_map.items():
            if norm_url in normalized_comp or normalized_comp in norm_url:
                return competitor_names.get(orig_url, orig_url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0])
        
        # Fallback to cleaning the URL
        return website_url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
    
    # Use proper competitor names from config with flexible matching
    clean_competitors = [get_competitor_name(comp) for comp in competitors]
    all_nodes = clean_competitors + topics

    # Build links with value aggregation to reduce clutter
    link_data = {}
    for _, row in df_long.iterrows():
        # Get the proper competitor name for this website
        comp_name = get_competitor_name(row["website"])
        
        try:
            comp_idx = clean_competitors.index(comp_name)
            topic_idx = topics.index(row["topic"]) + len(clean_competitors)
            key = (comp_idx, topic_idx)
            link_data[key] = link_data.get(key, 0) + 1
        except ValueError as e:
            print(f"DEBUG: Error finding index for {comp_name} or {row['topic']}: {e}")
            continue

    source, target, value = [], [], []
    for (s, t), v in link_data.items():
        source.append(s)
        target.append(t)
        value.append(v)

    # --- Sankey figure with improved styling ---
    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=25,  # Increased padding for better spacing
            thickness=20,  # Slightly thicker nodes
            line=dict(color="rgba(255,255,255,0.2)", width=2),
            label=all_nodes,
            color=["#3b82f6" if n in clean_competitors else "#8b5cf6" for n in all_nodes],
            hovertemplate="%{label}<br>Connections: %{value}<extra></extra>"
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color="rgba(59,130,246,0.3)" if competitor_group == "close" else "rgba(139,92,246,0.3)",
            hovertemplate="%{source.label} → %{target.label}<br>Strength: %{value}<extra></extra>"
        )
    )])

    fig.update_layout(
        title=f"🎯 Topic Flow — {competitor_group.capitalize()} Competitors (Top {len(topics)} Topics)",
        font=dict(size=13, color="#f1f5f9"),
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        height=800,  # Increased height for better visibility
        margin=dict(l=50, r=50, t=80, b=50)
    )

    return fig