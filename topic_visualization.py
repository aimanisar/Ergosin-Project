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
            # "📈 Website Metrics",
            "📊 Simple Topic Comparison",
            # "📉 Topic Trends",
            "🎯 Priority Matrix",
            # "⏳ Trend Timeline",
            # "🧭 Strategic Analysis"
        ])

        with tabs[0]:
            # st.subheader("Treemap of Topic Distribution")

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
            st.subheader("Simple Topic Comparison")
            visualizer.create_simple_topic_comparison(competitor_type=competitor_type)


        with tabs[2]:
            st.subheader("Topic Overlap Chord Diagram")

            try:
                df_cache = get_cached_data()
                if not df_cache.empty:
                    fig = create_topic_sankey(df, competitor_group="close", top_n=20)
                    st.plotly_chart(fig, use_container_width=True)

                else:
                    st.info("No cached data found — please scrape competitors first.")
            except Exception as e:
                st.error(f"Chord diagram error: {e}")



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
    if not isinstance(u, str):
        return ""
    return u.lower().replace("https://", "").replace("http://", "").replace("www.", "").strip('/')



def create_topic_network(df, competitor_group="close", top_n=20):
    """
    Build an interactive competitor–topic network graph for either close or international competitors.
    """

    # --- Filter based on competitor group (same logic as treemap uses) ---
    selected_sites = [normalize_url(s["url"]) for s in SITES if s.get("type") == f"competitor_{competitor_group}"]
    df["website_clean"] = df["website"].apply(normalize_url)
    df = df[df["website_clean"].isin(selected_sites)]

    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"No data available for {competitor_group.title()} competitors",
            template="plotly_dark", height=500
        )
        return fig

    # --- Extract and clean topics ---
    all_topics = []
    for topics in df["topics"].dropna():
        if isinstance(topics, list):
            all_topics.extend([t.strip() for t in topics if str(t).strip()])
        elif isinstance(topics, str):
            try:
                parsed = ast.literal_eval(topics)
                if isinstance(parsed, list):
                    all_topics.extend([t.strip() for t in parsed if str(t).strip()])
                else:
                    all_topics.extend([t.strip() for t in topics.split(',') if str(t).strip()])
            except Exception:
                all_topics.extend([t.strip() for t in topics.split(',') if str(t).strip()])

    top_topics = [t for t, _ in Counter(all_topics).most_common(top_n)]

    # --- Create bipartite graph ---
    G = nx.Graph()
    competitors = df["website"].unique()

    for comp in competitors:
        G.add_node(comp, type="competitor")

    for _, row in df.iterrows():
        site = row["website"]
        topics = row["topics"]
        if isinstance(topics, str):
            try:
                topics = ast.literal_eval(topics)
            except Exception:
                topics = [t.strip() for t in topics.split(',')]
        for t in topics:
            if t in top_topics:
                G.add_node(t, type="topic")
                G.add_edge(site, t)

    # --- Calculate attributes ---
    degree = dict(G.degree())
    for n in G.nodes:
        G.nodes[n]["size"] = 10 + degree[n] * 2

# --- Improved layout: balanced, consistent, centered ---
    pos = nx.spring_layout(G, k=1.2, iterations=100, seed=42)

    # --- Highlight the most connected (hub) competitor node ---
    for node, data in G.nodes(data=True):
        if data["type"] == "competitor" and degree[node] == max(degree.values()):
            data["size"] *= 1.4  # Slightly enlarge main hub node


    # --- Node colour palette ---
    COLOR_COMPETITOR = "#38bdf8"   # bright teal-blue
    COLOR_TOPIC = "#c084fc"        # lavender purple
    COLOR_EDGE = "rgba(148,163,184,0.35)"  # soft gray edge lines

    # --- Build Plotly figure ---
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    # Edges
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(color=COLOR_EDGE, width=0.8),
        hoverinfo="none"
    )

    # Nodes
    node_x, node_y, colors, sizes, labels, hover_texts = [], [], [], [], [], []
    for node, data in G.nodes(data=True):
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        sizes.append(data["size"])
        labels.append(node)
        if data["type"] == "competitor":
            colors.append(COLOR_COMPETITOR)
            hover_texts.append(f"<b>Competitor:</b> {node}<br>Connections: {degree[node]}")
        else:
            colors.append(COLOR_TOPIC)
            hover_texts.append(f"<b>Topic:</b> {node}<br>Linked Competitors: {degree[node]}")

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
            line=dict(width=1.4, color="rgba(255,255,255,0.15)"),
            opacity=0.95
        )
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
                # title=f"Topic Relationship Network — {competitor_group.title()} Competitors (Top {top_n} Keywords)",
        showlegend=False,
        hovermode="closest",
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        margin=dict(l=0, r=0, t=60, b=0),
        height=700,
    )
    # --- Center and balance layout visually ---
    fig.update_xaxes(showgrid=False, zeroline=False, visible=False, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(showgrid=False, zeroline=False, visible=False)
    fig.update_layout(autosize=True, margin=dict(l=20, r=20, t=60, b=20), height=600)

    return fig

def create_topic_sankey(df, competitor_group="close", top_n=20):
    """
    Create a Sankey diagram showing how competitors connect to shared topics.
    """
    # --- Normalize topics ---
    all_rows = []
    for _, row in df.iterrows():
        site = row["website"]
        topics = row.get("topics", [])
        if isinstance(topics, str):
            try:
                topics = ast.literal_eval(topics)
            except Exception:
                topics = [t.strip() for t in topics.split(",")]
        topics = [t.strip() for t in topics if t.strip()]
        for t in topics:
            all_rows.append({"website": site, "topic": t})

    df_long = pd.DataFrame(all_rows)
    top_topics = [t for t, _ in Counter(df_long["topic"]).most_common(top_n)]
    df_long = df_long[df_long["topic"].isin(top_topics)]

    # --- Build Sankey nodes and links ---
    competitors = df_long["website"].unique().tolist()
    topics = df_long["topic"].unique().tolist()
    all_nodes = competitors + topics

    source, target, value = [], [], []
    for _, row in df_long.iterrows():
        source.append(all_nodes.index(row["website"]))
        target.append(all_nodes.index(row["topic"]))
        value.append(1)

    # --- Sankey figure ---
    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20,
            thickness=18,
            line=dict(color="rgba(255,255,255,0.1)", width=1),
            label=all_nodes,
            color=["#38bdf8" if n in competitors else "#c084fc" for n in all_nodes],
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color="rgba(56,189,248,0.4)" if competitor_group == "close" else "rgba(249,115,22,0.4)"
        )
    )])

    fig.update_layout(
        title=f"Topic Flow — {competitor_group.capitalize()} Competitors (Top {top_n} Topics)",
        font=dict(size=12, color="#f1f5f9"),
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        height=700,
        margin=dict(l=20, r=20, t=60, b=20)
    )

    return fig