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

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from config import SITES
import plotly.express as px

from storage import load_cache


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
    
    def load_data(self, df=None, filter_type=None):
        """Load cached data and optionally filter by competitor type"""
        self.filter_type = filter_type 
        
        if df is None:
            from storage import load_cache
            df = load_cache()
        if df is None or df.empty:
            st.info("No data available for visualization.")
            return False

        # --- Normalize website column for matching ---
        df['website_clean'] = (
            df['website']
            .str.replace(r'^https?://', '', regex=True)  # remove http:// or https://
            .str.strip('/')                              # remove trailing slash
        )

        # Build competitor groups dynamically from config, also cleaned
        close_sites = [
            s["url"].replace("https://", "").replace("http://", "").strip('/')
            for s in SITES if s["type"] == "competitor_close"
        ]
        international_sites = [
            s["url"].replace("https://", "").replace("http://", "").strip('/')
                for s in SITES if s["type"] == "competitor_international"
            ]

            # Base website = ergosign
        self.base_data = df[df["website_clean"].str.contains("ergosign", case=False, na=False)]

            # Filter competitors by type
        if filter_type == "close":
                self.competitor_data = df[df["website_clean"].isin(close_sites)]
        elif filter_type == "international":
                self.competitor_data = df[df["website_clean"].isin(international_sites)]
        else:
                competitor_sites = close_sites + international_sites
                self.competitor_data = df[df["website_clean"].isin(competitor_sites)]

        self.df = df

        self.df = df

        # Debug logging
        print(f"DEBUG — Loaded data shape: {df.shape}")
        print(f"DEBUG — Base sites found: {self.base_data['website_clean'].unique().tolist()}")
        print(f"DEBUG — Competitors ({filter_type}): {self.competitor_data['website_clean'].unique().tolist()}")


        return True


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
        for topic in all_topics:
            base_count = top_base.get(topic, 0)
            comp_count = top_competitor.get(topic, 0)
            total_count = base_count + comp_count
            
            comparison_data.append({
                'Topic': topic,
                'Base Website': base_count,
                'Competitors': comp_count,
                'Total': total_count
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        comparison_df = comparison_df.sort_values('Total', ascending=True)
        
        # Create simple horizontal bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=comparison_df['Topic'],
            x=comparison_df['Base Website'],
            name='Your Website',
            orientation='h',
            marker_color='#1f77b4',
            text=comparison_df['Base Website'],
            textposition='auto',
        ))
        
        fig.add_trace(go.Bar(
            y=comparison_df['Topic'],
            x=comparison_df['Competitors'],
            name='Competitors',
            orientation='h',
            marker_color='#ff7f0e',
            text=comparison_df['Competitors'],
            textposition='auto',
        ))
        
        fig.update_layout(
            title='Topic Comparison: Your Website vs Competitors',
            xaxis_title='Number of Mentions',
            yaxis_title='Topics',
            barmode='group',
            height=max(600, len(comparison_df) * 25),  # Dynamic height based on number of topics
            showlegend=True,
            template='plotly_white',
            margin=dict(l=200, r=50, t=80, b=50)  # Add left margin for topic labels
        )
        # fig = apply_plotly_theme(fig, mode)
        # st.plotly_chart(fig, use_container_width=True)

        
        # Improve y-axis labels to prevent overlapping
        fig.update_yaxes(
            tickfont=dict(size=10),
            tickangle=0
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"plot_{competitor_type}_{id(fig)}")

        
        # Simple insights
        st.subheader("Key Findings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Your Top Topics:**")
            for topic, count in base_topics.most_common(5):
                st.write(f"• {topic}: {count} mentions")
        
        with col2:
            st.write("**Competitor Top Topics:**")
            for topic, count in competitor_topics.most_common(5):
                st.write(f"• {topic}: {count} mentions")
    
    def create_topic_comparison_chart(self, competitor_type="default"):
        """Create a comparison chart of top topics"""
        if self.base_data.empty or self.competitor_data.empty:
            st.warning("Need both base and competitor data for comparison")
            return
        
        # Extract topics
        base_topics = self.extract_topics(self.base_data)
        competitor_topics = self.extract_topics(self.competitor_data)
        
        # Get top 10 topics for each
        top_base = dict(base_topics.most_common(10))
        top_competitor = dict(competitor_topics.most_common(10))
        
        # Create comparison data
        all_topics = set(list(top_base.keys()) + list(top_competitor.keys()))
        
        comparison_data = []
        for topic in all_topics:
            comparison_data.append({
                'Topic': topic,
                'Base Website': top_base.get(topic, 0),
                'Competitors': top_competitor.get(topic, 0)
            })
        
        # Sort by total mentions
        comparison_df = pd.DataFrame(comparison_data)
        comparison_df['Total'] = comparison_df['Base Website'] + comparison_df['Competitors']
        comparison_df = comparison_df.sort_values('Total', ascending=True)
        
        # Create horizontal bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=comparison_df['Topic'],
            x=comparison_df['Base Website'],
            name='Base Website (Ergosign)',
            orientation='h',
            marker_color='#1f77b4',
            text=comparison_df['Base Website'],
            textposition='auto',
        ))
        
        fig.add_trace(go.Bar(
            y=comparison_df['Topic'],
            x=comparison_df['Competitors'],
            name='Competitors',
            orientation='h',
            marker_color='#ff7f0e',
            text=comparison_df['Competitors'],
            textposition='auto',
        ))
        
        fig.update_layout(
            title='Topic Comparison: Base Website vs Competitors',
            xaxis_title='Number of Mentions',
            yaxis_title='Topics',
            barmode='group',
            height=600,
            showlegend=True,
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"plot_{competitor_type}_{id(fig)}")

    
    def create_topic_trend_chart(self, competitor_type="default"):
        """Create a trend chart showing topic distribution"""
        if self.df.empty:
            return
        
        # Extract all topics with website info
        topic_data = []
        for _, row in self.df.iterrows():
            if row['topics'] and row['topics'] != '[]':
                topics = [topic.strip() for topic in str(row['topics']).split(',')]
                website_type = 'Base' if 'ergosign' in row['website'].lower() else 'Competitor'
                for topic in topics:
                    topic_data.append({
                        'Topic': topic,
                        'Website': row['website'],
                        'Type': website_type,
                        'Page': row['page_name']
                    })
        
        if not topic_data:
            st.warning("No topic data available for visualization")
            return
        
        topic_df = pd.DataFrame(topic_data)
        
        # Get top 15 topics
        top_topics = topic_df['Topic'].value_counts().head(15).index.tolist()
        filtered_df = topic_df[topic_df['Topic'].isin(top_topics)]
        
        # Create stacked bar chart
        fig = px.bar(
            filtered_df, 
            x='Topic', 
            color='Type',
            title='Topic Distribution by Website Type',
            color_discrete_map={'Base': '#1f77b4', 'Competitor': '#ff7f0e'},
            height=500
        )
        
        fig.update_layout(
            xaxis_tickangle=-45,
            template='plotly_white',
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True, key=f"plot_{competitor_type}_{id(fig)}")

    
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

    
    def create_topic_cloud_data(self):
        """Create data for topic cloud visualization"""
        if self.df.empty:
            return
        
        # Extract all topics
        all_topics = []
        for topics_str in self.df['topics'].dropna():
            if topics_str and topics_str != '[]':
                topics = [topic.strip() for topic in str(topics_str).split(',')]
                all_topics.extend(topics)
        
        # Count topics
        topic_counts = Counter(all_topics)
        
        # Create word cloud data
        word_cloud_data = []
        for topic, count in topic_counts.most_common(20):
            word_cloud_data.append({
                'text': topic,
                'value': count,
                'size': min(count * 10, 100)  # Scale for visualization
            })
        
        return word_cloud_data
    
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
        
<<<<<<< Updated upstream
        # Collect topics for each website (keep frequency data)
        website_topics = {}
        for website in websites:
            website_data = self.df[self.df['website'] == website]
            topics = []
            
            for topics_str in website_data['topics'].dropna():
                if topics_str and topics_str != '[]':
                    topic_list = [topic.strip() for topic in str(topics_str).split(',')]
                    topics.extend(topic_list)
            
            website_topics[website] = topics  # Keep all mentions for accurate counting
        
        # Create professional visualizations
        self._create_topic_coverage_heatmap(website_topics, base_website, competitor_websites)
        self._create_competitive_positioning_chart(website_topics, base_website, competitor_websites)
    
    def _create_topic_coverage_heatmap(self, website_topics, base_website, competitor_websites):
        """Create a smart, scalable topic coverage visualization"""
        st.subheader("🎯 Smart Competitive Analysis Dashboard")
        
        # Get all unique topics
        all_topics = set()
        for topics in website_topics.values():
            all_topics.update(topics)
        
        all_topics = sorted(list(all_topics))
        all_websites = [base_website] + competitor_websites
        
        # Smart filtering options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Filter by topic importance
            topic_importance = st.selectbox(
                "Filter by Topic Importance:",
                ["All Topics", "High Impact (5+ mentions)", "Medium Impact (2-4 mentions)", "Low Impact (1 mention)"],
                key="topic_filter"
            )
        
        with col2:
            # Filter by competitor group
            competitor_filter = st.selectbox(
                "Filter by Competitor Group:",
                ["All Competitors", "Top 5 Competitors", "Top 10 Competitors", "Ergosign vs Top 3"],
                key="competitor_filter"
            )
        
        with col3:
            # Show only gaps
            show_gaps_only = st.checkbox("Show Only Ergosign Gaps", value=False)
        
        # Apply filters
        filtered_topics = self._filter_topics_by_importance(all_topics, website_topics, topic_importance)
        filtered_websites = self._filter_websites_by_group(all_websites, competitor_filter, base_website)
        
        if show_gaps_only:
            filtered_topics = self._filter_ergosign_gaps(filtered_topics, website_topics, base_website)
        
        # Show only the Priority List
        self._create_topic_priority_list(filtered_topics, website_topics, base_website)
    
    def _filter_topics_by_importance(self, all_topics, website_topics, importance_filter):
        """Filter topics based on importance/mention frequency"""
        if importance_filter == "All Topics":
            return all_topics
        
        # Count total mentions across all websites
        topic_counts = {}
        for topic in all_topics:
            count = sum(website_topics.get(website, []).count(topic) for website in website_topics.keys())
            topic_counts[topic] = count
        
        if importance_filter == "High Impact (5+ mentions)":
            return [topic for topic, count in topic_counts.items() if count >= 5]
        elif importance_filter == "Medium Impact (2-4 mentions)":
            return [topic for topic, count in topic_counts.items() if 2 <= count < 5]
        elif importance_filter == "Low Impact (1 mention)":
            return [topic for topic, count in topic_counts.items() if count == 1]
        
        return all_topics
    
    def _filter_websites_by_group(self, all_websites, group_filter, base_website):
        """Filter websites by competitor group"""
        if group_filter == "All Competitors":
            return all_websites
        elif group_filter == "Top 5 Competitors":
            # Return base + top 5 competitors (simplified for now)
            return [base_website] + all_websites[1:6]
        elif group_filter == "Top 10 Competitors":
            return [base_website] + all_websites[1:11]
        elif group_filter == "Ergosign vs Top 3":
            return [base_website] + all_websites[1:4]
        
        return all_websites
    
    def _filter_ergosign_gaps(self, topics, website_topics, base_website):
        """Filter to show only topics where Ergosign has gaps"""
        ergosign_topics = set(website_topics.get(base_website, []))
        return [topic for topic in topics if topic not in ergosign_topics]
    
    
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
    
    def _create_competitive_positioning_chart(self, website_topics, base_website, competitor_websites):
        """Create competitive positioning analysis"""
        st.subheader("Competitive Positioning")
        
        # Calculate metrics for each website
        all_topics = set()
        for topics in website_topics.values():
            all_topics.update(topics)
        
        website_metrics = []
        for website in [base_website] + competitor_websites:
            topics = website_topics.get(website, [])
            coverage_pct = (len(topics) / len(all_topics) * 100) if all_topics else 0
            
            website_metrics.append({
                'Website': website,
                'Topic Count': len(topics),
                'Coverage %': coverage_pct,
                'Type': 'Base' if website == base_website else 'Competitor'
            })
        
        metrics_df = pd.DataFrame(website_metrics)
        
        # Create scatter plot
        fig = go.Figure()
        
        # Base website
        base_data = metrics_df[metrics_df['Type'] == 'Base']
        if not base_data.empty:
            fig.add_trace(go.Scatter(
                x=base_data['Topic Count'],
                y=base_data['Coverage %'],
                mode='markers+text',
                text=base_data['Website'],
                textposition='top center',
                marker=dict(size=15, color='red', symbol='star'),
                name='Your Website'
            ))
        
        # Competitors
        comp_data = metrics_df[metrics_df['Type'] == 'Competitor']
        if not comp_data.empty:
            fig.add_trace(go.Scatter(
                x=comp_data['Topic Count'],
                y=comp_data['Coverage %'],
                mode='markers+text',
                text=comp_data['Website'],
                textposition='top center',
                marker=dict(size=12, color='blue'),
                name='Competitors'
            ))
        
        fig.update_layout(
            title='Competitive Positioning: Topic Count vs Coverage',
            xaxis_title='Number of Topics',
            yaxis_title='Coverage Percentage',
            height=500,
            template='plotly_white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _create_llm_visualizations(self, analysis_result):
        """Create visualizations based on LLM analysis results"""
        if 'trending_topics' not in analysis_result:
=======
        # ✅ Use only filtered competitor data for the current tab
        competitor_websites = self.competitor_data['website'].unique()
        
        if len(competitor_websites) == 0:
            st.info(f"No competitors found for {self.filter_type} group")
>>>>>>> Stashed changes
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


    
    # def _create_topic_coverage_heatmap(
    #     self, website_topics, base_website, competitor_websites, competitor_type="default"
    # ):
    #     """Create a professional topic coverage heatmap"""

    #     st.subheader("Topic Coverage Matrix")

    #     # Ensure base + competitors are actually present
    #     all_websites = [base_website] + [
    #         w for w in competitor_websites if w in website_topics
    #     ]

    #     if not all_websites or len(all_websites) < 2:
    #         st.info(f"No {competitor_type} competitors available for heatmap.")
    #         return

    #     # Collect all unique topics
    #     all_topics = sorted({
    #         topic
    #         for website in all_websites
    #         for topic in website_topics.get(website, [])
    #     })

    #     if not all_topics:
    #         st.info(f"No topics found for {competitor_type} competitors.")
    #         return

    #     # Build coverage matrix
    #     coverage_matrix = []
    #     for website in all_websites:
    #         topics = website_topics.get(website, [])
    #         row = [1 if topic in topics else 0 for topic in all_topics]
    #         coverage_matrix.append(row)

    #     # Plot heatmap
    #     fig = go.Figure(data=go.Heatmap(
    #         z=coverage_matrix,
    #         x=all_topics,
    #         y=all_websites,
    #         colorscale="RdYlBu_r",
    #         showscale=True,
    #         colorbar=dict(title="Coverage"),
    #         hoverongaps=False,
    #         hovertemplate="<b>%{y}</b><br>Topic: %{x}<br>Covered: %{z}<extra></extra>"
    #     ))

    #     fig.update_layout(
    #         title=f"Topic Coverage Across Websites ({competitor_type.title()})",
    #         xaxis_title="Topics",
    #         yaxis_title="Websites",
    #         height=max(400, len(all_websites) * 30),
    #         template="plotly_white",
    #         margin=dict(l=150, r=50, t=80, b=100)
    #     )

    #     fig.update_xaxes(tickangle=-45, tickfont=dict(size=9))
    #     fig.update_yaxes(tickfont=dict(size=10))

    #     st.plotly_chart(
    #         fig,
    #         use_container_width=True,
    #         key=f"heatmap_{competitor_type}"
    #     )


    
    # def _create_competitive_positioning_chart(
    #     self, website_topics, base_website, competitor_websites, competitor_type="default"
    # ):
    #     """Create a competitive positioning scatter plot (Base vs Competitors)."""

    #     st.subheader("Competitive Positioning")

    #     # ---------------- Prepare Metrics ----------------
    #     metrics = []
    #     for website, topics in website_topics.items():
    #         coverage = len(topics)

    #         if website == base_website:
    #             metrics.append([website, coverage, "Base"])
    #         else:
    #             metrics.append([website, coverage, "Competitor"])

    #     # Create DataFrame
    #     metrics_df = pd.DataFrame(metrics, columns=["Website", "Coverage", "Type"])

    #     # Safety check
    #     if metrics_df.empty or "Type" not in metrics_df.columns:
    #         st.warning("No data available for competitive positioning chart.")
    #         return

    #     # ---------------- Scatter Plot ----------------
    #     fig = go.Figure()

    #     # Base website (ergosign)
    #     base_data = metrics_df[metrics_df["Type"] == "Base"]
    #     if not base_data.empty:
    #         fig.add_trace(go.Scatter(
    #             x=base_data["Coverage"],
    #             y=[15] * len(base_data),  # Example Y placeholder (adjust as needed)
    #             mode="markers+text",
    #             marker=dict(size=14, color="red", symbol="star"),
    #             name="Your Website",
    #             text=base_data["Website"],
    #             textposition="top center"
    #         ))

    #     # Competitors
    #     competitor_data = metrics_df[metrics_df["Type"] == "Competitor"]
    #     if not competitor_data.empty:
    #         fig.add_trace(go.Scatter(
    #             x=competitor_data["Coverage"],
    #             y=[i * 5 for i in range(len(competitor_data))],  # Example Y values
    #             mode="markers+text",
    #             marker=dict(size=12, color="blue"),
    #             name="Competitors",
    #             text=competitor_data["Website"],
    #             textposition="top center"
    #         ))

    #     # ---------------- Layout ----------------
    #     fig.update_layout(
    #         title=f"Competitive Positioning ({competitor_type.title()})",
    #         xaxis_title="Number of Topics",
    #         yaxis_title="Coverage (placeholder %)",  # adjust if you calculate coverage %
    #         template="plotly_white",
    #         height=500
    #     )

    #     # ---------------- Render ----------------
    #     st.plotly_chart(
    #         fig, 
    #         use_container_width=True, 
    #         key=f"competitive_scatter_{competitor_type}"
    #     )


    def _create_topic_frequency_chart(self, website_topics, competitor_type="default"):
        """Horizontal bar chart of top topics among competitors"""

        # Flatten all competitor topics
        all_topics = []
        for site, topics in website_topics.items():
            if site not in self.base_data['website'].unique():  # exclude base Ergonsign
                all_topics.extend(topics)

        if not all_topics:
            st.info(f"No topics available for {competitor_type} competitors.")
            return

        topic_counts = pd.Series(all_topics).value_counts().reset_index()
        topic_counts.columns = ["Topic", "Frequency"]

        # Limit to top 10 for readability
        topic_counts = topic_counts.head(10)

        fig = px.bar(
            topic_counts.sort_values("Frequency", ascending=True),
            x="Frequency",
            y="Topic",
            orientation="h",
            title=f"Top Topics Among {competitor_type.capitalize()} Competitors",
            text="Frequency",
            color_discrete_sequence=["#1f77b4"]  # clean blue color
        )

        fig.update_traces(textposition="inside", insidetextanchor="middle")
        fig.update_layout(
            template="plotly_white",
            height=450,
            xaxis_title="Frequency",
            yaxis_title="Topic",
            margin=dict(l=150, r=50, t=60, b=50)
        )
        st.plotly_chart(fig, use_container_width=True, key=f"bar_{competitor_type}")



    # def _create_topic_distribution_pie(self, website_topics, competitor_type="default"):
    #     """Pie chart of topic distribution"""
    #     import plotly.express as px

    #     all_topics = []
    #     for site, topics in website_topics.items():
    #         if site not in self.base_data['website'].unique():  # exclude base Ergonsign
    #             all_topics.extend(topics)

    #     if not all_topics:
    #         st.info(f"No topics available for {competitor_type} competitors.")
    #         return

    #     topic_counts = pd.Series(all_topics).value_counts().reset_index()
    #     topic_counts.columns = ["Topic", "Count"]

    #     fig = px.pie(
    #         topic_counts.head(10),
    #         names="Topic", values="Count",
    #         title=f"Topic Distribution – {competitor_type.capitalize()} Competitors",
    #         hole=0.4
    #     )
    #     st.plotly_chart(fig, use_container_width=True, key=f"pie_{competitor_type}")

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

    # def _create_llm_visualizations(self, analysis_result, competitor_type="default"):
    #     """Create visualizations based on LLM analysis results"""
    #     if 'trending_topics' not in analysis_result:
    #         return
        
    #     trending = analysis_result['trending_topics']
        
    #     # Create topic trend visualization
    #     if 'topic_scores' in trending:
    #         topic_scores = trending['topic_scores']
            
    #         # Create bar chart for trending topics
    #         fig = go.Figure()
            
    #         topics = list(topic_scores.keys())
    #         scores = list(topic_scores.values())
            
    #         fig.add_trace(go.Bar(
    #             x=topics,
    #             y=scores,
    #             marker_color='lightblue',
    #             text=scores,
    #             textposition='auto'
    #         ))
            
    #         fig.update_layout(
    #             title='AI-Identified Trending Topics',
    #             xaxis_title='Topics',
    #             yaxis_title='Trend Score',
    #             height=500,
    #             template='plotly_white'
    #         )
            
    #         fig.update_xaxes(tickangle=-45)
    #         st.plotly_chart(fig, use_container_width=True, key=f"plot_{competitor_type}_{id(fig)}")

    
    def _create_fallback_analysis(self, website_topics, base_website, competitor_websites, competitor_type="default"):
        """Fallback analysis when LLM is not available"""
        st.subheader("📊 Basic Topic Analysis")
        
        # Simple topic comparison
        base_topics = set(website_topics.get(base_website, []))
        all_competitor_topics = set()
        
        for comp_website in competitor_websites:
            all_competitor_topics.update(website_topics.get(comp_website, []))
        
        # Find unique and common topics
        unique_to_base = base_topics - all_competitor_topics
        unique_to_competitors = all_competitor_topics - base_topics
        common_topics = base_topics & all_competitor_topics
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**Your Unique Topics:**")
            for topic in list(unique_to_base)[:10]:
                st.write(f"• {topic}")
        
        with col2:
            st.write("**Competitor Unique Topics:**")
            for topic in list(unique_to_competitors)[:10]:
                st.write(f"• {topic}")
        
        with col3:
            st.write("**Common Topics:**")
            for topic in list(common_topics)[:10]:
                st.write(f"• {topic}")
        
        # Simple metrics
        st.subheader("Basic Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Your Topics", len(base_topics))
        
        with col2:
            st.metric("Competitor Topics", len(all_competitor_topics))
        
        with col3:
            st.metric("Common Topics", len(common_topics))
        
        with col4:
            st.metric("Your Unique", len(unique_to_base))

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

    # def create_trend_timeline(self, competitor_type="default"):
    #     """Create a trend timeline for month-to-month tracking"""
    #     if self.df.empty:
    #         return
        
    #     # Check if we have date information
    #     if 'last_scraped' not in self.df.columns:
    #         st.warning("No date information available for trend analysis. Add 'last_scraped' column to enable timeline tracking.")
    #         return
        
    #     # Convert last_scraped to datetime
    #     try:
    #         self.df['scrape_date'] = pd.to_datetime(self.df['last_scraped'])
    #         self.df['month'] = self.df['scrape_date'].dt.to_period('M')
    #     except:
    #         st.warning("Could not parse date information for trend analysis")
    #         return
        
    #     # Get unique months
    #     months = sorted(self.df['month'].unique())
    #     if len(months) < 2:
    #         st.info("Need data from at least 2 different months to show trends")
    #         return
        
    #     # Create trend data
    #     trend_data = []
    #     for month in months:
    #         month_data = self.df[self.df['month'] == month]
            
    #         # Extract topics for this month
    #         month_topics = []
    #         for topics_str in month_data['topics'].dropna():
    #             if topics_str and topics_str != '[]':
    #                 topics = [topic.strip() for topic in str(topics_str).split(',')]
    #                 month_topics.extend(topics)
            
    #         topic_counts = Counter(month_topics)
            
    #         # Separate base and competitor topics
    #         base_data = month_data[month_data['website'].str.contains('ergosign', case=False, na=False)]
    #         comp_data = month_data[~month_data['website'].str.contains('ergosign', case=False, na=False)]
            
    #         base_topics = []
    #         for topics_str in base_data['topics'].dropna():
    #             if topics_str and topics_str != '[]':
    #                 topics = [topic.strip() for topic in str(topics_str).split(',')]
    #                 base_topics.extend(topics)
            
    #         comp_topics = []
    #         for topics_str in comp_data['topics'].dropna():
    #             if topics_str and topics_str != '[]':
    #                 topics = [topic.strip() for topic in str(topics_str).split(',')]
    #                 comp_topics.extend(topics)
            
    #         base_counts = Counter(base_topics)
    #         comp_counts = Counter(comp_topics)
            
    #         trend_data.append({
    #             'Month': str(month),
    #             'Total Topics': len(topic_counts),
    #             'Base Topics': len(base_counts),
    #             'Competitor Topics': len(comp_counts),
    #             'Total Mentions': sum(topic_counts.values()),
    #             'Base Mentions': sum(base_counts.values()),
    #             'Competitor Mentions': sum(comp_counts.values())
    #         })
        
    #     trend_df = pd.DataFrame(trend_data)
        
    #     # Create trend charts
    #     fig = make_subplots(
    #         rows=2, cols=2,
    #         subplot_titles=(
    #             'Topic Count Trends',
    #             'Mention Volume Trends',
    #             'Base vs Competitor Topics',
    #             'Market Share Trends'
    #         ),
    #         specs=[[{"type": "scatter"}, {"type": "scatter"}],
    #                [{"type": "scatter"}, {"type": "scatter"}]]
    #     )
        
    #     # 1. Topic count trends
    #     fig.add_trace(
    #         go.Scatter(
    #             x=trend_df['Month'],
    #             y=trend_df['Total Topics'],
    #             mode='lines+markers',
    #             name='Total Topics',
    #             line=dict(color='#1f77b4', width=3)
    #         ),
    #         row=1, col=1
    #     )
        
    #     fig.add_trace(
    #         go.Scatter(
    #             x=trend_df['Month'],
    #             y=trend_df['Base Topics'],
    #             mode='lines+markers',
    #             name='Base Topics',
    #             line=dict(color='#2E8B57', width=2)
    #         ),
    #         row=1, col=1
    #     )
        
    #     fig.add_trace(
    #         go.Scatter(
    #             x=trend_df['Month'],
    #             y=trend_df['Competitor Topics'],
    #             mode='lines+markers',
    #             name='Competitor Topics',
    #             line=dict(color='#FF6B6B', width=2)
    #         ),
    #         row=1, col=1
    #     )
        
    #     # 2. Mention volume trends
    #     fig.add_trace(
    #         go.Scatter(
    #             x=trend_df['Month'],
    #             y=trend_df['Total Mentions'],
    #             mode='lines+markers',
    #             name='Total Mentions',
    #             line=dict(color='#FF7F0E', width=3),
    #             showlegend=False
    #         ),
    #         row=1, col=2
    #     )
        
    #     fig.add_trace(
    #         go.Scatter(
    #             x=trend_df['Month'],
    #             y=trend_df['Base Mentions'],
    #             mode='lines+markers',
    #             name='Base Mentions',
    #             line=dict(color='#2E8B57', width=2),
    #             showlegend=False
    #         ),
    #         row=1, col=2
    #     )
        
    #     fig.add_trace(
    #         go.Scatter(
    #             x=trend_df['Month'],
    #             y=trend_df['Competitor Mentions'],
    #             mode='lines+markers',
    #             name='Competitor Mentions',
    #             line=dict(color='#FF6B6B', width=2),
    #             showlegend=False
    #         ),
    #         row=1, col=2
    #     )
        
    #     # 3. Base vs Competitor comparison
    #     fig.add_trace(
    #         go.Scatter(
    #             x=trend_df['Base Topics'],
    #             y=trend_df['Competitor Topics'],
    #             mode='markers+text',
    #             text=trend_df['Month'],
    #             textposition='top center',
    #             marker=dict(
    #                 size=trend_df['Total Topics'] * 2,
    #                 color=trend_df['Total Topics'],
    #                 colorscale='Viridis',
    #                 showscale=True,
    #                 colorbar=dict(title="Total Topics")
    #             ),
    #             name='Monthly Comparison',
    #             showlegend=False
    #         ),
    #         row=2, col=1
    #     )
        
    #     # 4. Market share trends
    #     trend_df['Base Share'] = (trend_df['Base Mentions'] / trend_df['Total Mentions'] * 100).fillna(0)
    #     trend_df['Competitor Share'] = (trend_df['Competitor Mentions'] / trend_df['Total Mentions'] * 100).fillna(0)
        
    #     fig.add_trace(
    #         go.Scatter(
    #             x=trend_df['Month'],
    #             y=trend_df['Base Share'],
    #             mode='lines+markers',
    #             name='Base Market Share',
    #             line=dict(color='#2E8B57', width=3),
    #             fill='tonexty',
    #             showlegend=False
    #         ),
    #         row=2, col=2
    #     )
        
    #     fig.add_trace(
    #         go.Scatter(
    #             x=trend_df['Month'],
    #             y=trend_df['Competitor Share'],
    #             mode='lines+markers',
    #             name='Competitor Market Share',
    #             line=dict(color='#FF6B6B', width=3),
    #             fill='tozeroy',
    #             showlegend=False
    #         ),
    #         row=2, col=2
    #     )
        
    #     fig.update_layout(
    #         title='📈 Topic Trends Timeline - Month-to-Month Analysis',
    #         height=800,
    #         template='plotly_white',
    #         showlegend=True
    #     )
        
    #     # Update axes labels
    #     fig.update_xaxes(title_text="Month", row=1, col=1)
    #     fig.update_yaxes(title_text="Topic Count", row=1, col=1)
    #     fig.update_xaxes(title_text="Month", row=1, col=2)
    #     fig.update_yaxes(title_text="Mention Count", row=1, col=2)
    #     fig.update_xaxes(title_text="Base Topics", row=2, col=1)
    #     fig.update_yaxes(title_text="Competitor Topics", row=2, col=1)
    #     fig.update_xaxes(title_text="Month", row=2, col=2)
    #     fig.update_yaxes(title_text="Market Share %", row=2, col=2)
        
    #     st.plotly_chart(fig, use_container_width=True, key=f"plot_{competitor_type}_{id(fig)}")

        
    #     # Trend insights
    #     st.subheader("📊 Trend Insights")
        
    #     col1, col2, col3 = st.columns(3)
        
    #     with col1:
    #         # Calculate growth rates
    #         if len(trend_df) >= 2:
    #             latest = trend_df.iloc[-1]
    #             previous = trend_df.iloc[-2]
                
    #             topic_growth = ((latest['Total Topics'] - previous['Total Topics']) / previous['Total Topics'] * 100) if previous['Total Topics'] > 0 else 0
    #             st.metric("Topic Growth Rate", f"{topic_growth:+.1f}%")
        
    #     with col2:
    #         if len(trend_df) >= 2:
    #             mention_growth = ((latest['Total Mentions'] - previous['Total Mentions']) / previous['Total Mentions'] * 100) if previous['Total Mentions'] > 0 else 0
    #             st.metric("Mention Growth Rate", f"{mention_growth:+.1f}%")
        
    #     with col3:
    #         if len(trend_df) >= 2:
    #             share_change = latest['Base Share'] - previous['Base Share']
    #             st.metric("Market Share Change", f"{share_change:+.1f}%")
        
    #     # Trend recommendations
    #     st.markdown("---")
    #     st.subheader("🎯 Trend-Based Recommendations")
        
    #     if len(trend_df) >= 2:
    #         latest = trend_df.iloc[-1]
    #         previous = trend_df.iloc[-2]
            
    #         col1, col2 = st.columns(2)
            
    #         with col1:
    #             if latest['Base Topics'] < previous['Base Topics']:
    #                 st.write("**⚠️ Declining Topic Diversity:**")
    #                 st.write("• Focus on expanding topic coverage")
    #                 st.write("• Analyze competitor topics for inspiration")
    #             elif latest['Base Topics'] > previous['Base Topics']:
    #                 st.write("**✅ Growing Topic Diversity:**")
    #                 st.write("• Continue expanding topic coverage")
    #                 st.write("• Monitor competitor response")
            
    #         with col2:
    #             if latest['Base Share'] < previous['Base Share']:
    #                 st.write("**⚠️ Losing Market Share:**")
    #                 st.write("• Increase content frequency")
    #                 st.write("• Focus on high-impact topics")
    #             elif latest['Base Share'] > previous['Base Share']:
    #                 st.write("**✅ Gaining Market Share:**")
    #                 st.write("• Maintain current strategy")
    #                 st.write("• Consider expanding successful topics")

    def create_strategic_analysis(self, competitor_type="default"):
        """Create strategic competitive analysis"""
        if self.base_data.empty or self.competitor_data.empty:
            st.warning("Need both base and competitor data for strategic analysis")
            return
        
        # Extract topics
        base_topics = self.extract_topics(self.base_data)
        competitor_topics = self.extract_topics(self.competitor_data)
        
        # Calculate strategic metrics
        all_topics = set(list(base_topics.keys()) + list(competitor_topics.keys()))
        
        strategic_data = []
        for topic in all_topics:
            base_count = base_topics.get(topic, 0)
            comp_count = competitor_topics.get(topic, 0)
            total_count = base_count + comp_count
            
            # Strategic positioning
            if base_count > comp_count:
                position = "Market Leader"
                opportunity = "Maintain Leadership"
            elif comp_count > base_count:
                position = "Market Follower"
                opportunity = "Catch Up Opportunity"
            else:
                position = "Market Parity"
                opportunity = "Differentiation Opportunity"
            
            # Calculate growth potential
            growth_potential = "High" if total_count >= 3 else ("Medium" if total_count >= 2 else "Low")
            
            strategic_data.append({
                'Topic': topic,
                'Base Count': base_count,
                'Competitor Count': comp_count,
                'Total Market': total_count,
                'Position': position,
                'Opportunity': opportunity,
                'Growth Potential': growth_potential,
                'Market Share': (base_count / total_count * 100) if total_count > 0 else 0
            })
        
        strategic_df = pd.DataFrame(strategic_data)
        
        # Create strategic analysis chart
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Market Position Analysis',
                'Growth Potential by Topic',
                'Strategic Opportunities',
                'Market Share Distribution'
            ),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "pie"}, {"type": "bar"}]]
        )
        
        # 1. Market position
        position_counts = strategic_df['Position'].value_counts()
        fig.add_trace(
            go.Bar(
                x=position_counts.index,
                y=position_counts.values,
                name='Market Position',
                marker_color=['#2E8B57', '#FF6B6B', '#FFA500']
            ),
            row=1, col=1
        )
        
        # 2. Growth potential
        growth_counts = strategic_df['Growth Potential'].value_counts()
        fig.add_trace(
            go.Bar(
                x=growth_counts.index,
                y=growth_counts.values,
                name='Growth Potential',
                marker_color=['#FF6B6B', '#FFA500', '#2E8B57']
            ),
            row=1, col=2
        )
        
        # 3. Strategic opportunities
        opportunity_counts = strategic_df['Opportunity'].value_counts()
        fig.add_trace(
            go.Pie(
                labels=opportunity_counts.index,
                values=opportunity_counts.values,
                name="Opportunities",
                marker_colors=['#4ECDC4', '#45B7D1', '#96CEB4']
            ),
            row=2, col=1
        )
        
        # 4. Top market share topics
        top_market_share = strategic_df.nlargest(10, 'Market Share')
        fig.add_trace(
            go.Bar(
                x=top_market_share['Topic'],
                y=top_market_share['Market Share'],
                name='Market Share %',
                marker_color='#8A2BE2'
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title='🎯 Strategic Competitive Analysis',
            height=800,
            template='plotly_white',
            showlegend=False
        )
        
        fig.update_xaxes(tickangle=-45, row=2, col=2)
        
        st.plotly_chart(fig, use_container_width=True, key=f"plot_{competitor_type}_{id(fig)}")

        
        # Strategic recommendations
        st.subheader("💡 Strategic Recommendations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🚀 High-Priority Actions:**")
            leaders = strategic_df[strategic_df['Position'] == 'Market Leader'].head(3)
            for _, row in leaders.iterrows():
                st.write(f"• **{row['Topic']}**: Maintain leadership ({(row['Market Share']):.1f}% share)")
            
            st.write("**⚡ Quick Wins:**")
            followers = strategic_df[strategic_df['Position'] == 'Market Follower'].head(3)
            for _, row in followers.iterrows():
                st.write(f"• **{row['Topic']}**: Focus on catching up ({(row['Market Share']):.1f}% share)")
        
        with col2:
            st.write("**🎯 Growth Opportunities:**")
            high_growth = strategic_df[strategic_df['Growth Potential'] == 'High'].head(3)
            for _, row in high_growth.iterrows():
                st.write(f"• **{row['Topic']}**: High market activity ({row['Total Market']} mentions)")
            
            st.write("**🔍 Market Gaps:**")
            low_activity = strategic_df[strategic_df['Total Market'] == 1].head(3)
            for _, row in low_activity.iterrows():
                st.write(f"• **{row['Topic']}**: Underserved market opportunity")

    def display_metrics(self):
        """Display key metrics"""
        if self.df.empty:
            return
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Websites", len(self.df['website'].unique()))
        
        with col2:
            st.metric("Total Pages", len(self.df))
        
        with col3:
            all_topics = []
            for topics_str in self.df['topics'].dropna():
                if topics_str and topics_str != '[]':
                    topics = [topic.strip() for topic in str(topics_str).split(',')]
                    all_topics.extend(topics)
            st.metric("Unique Topics", len(set(all_topics)))
        
        with col4:
            base_pages = len(self.base_data) if not self.base_data.empty else 0
            competitor_pages = len(self.competitor_data) if not self.competitor_data.empty else 0
            st.metric("Base vs Competitor Pages", f"{base_pages} : {competitor_pages}")

def show_topic_visualization(df=None, competitor_type=None, mode="light"):
    """Main function to display topic visualizations with filtering for competitor groups"""
    
    ## Dynamic header
    if competitor_type == "close":
        st.header("📊 Topic Analysis – Close Competitors")
    elif competitor_type == "international":
        st.header("📊 Topic Analysis – International Competitors")
    else:
        st.header("📊 Topic Analysis & Comparison")

    visualizer = TopicVisualizer()

    # Load filtered data
    if not visualizer.load_data(df=df, filter_type=competitor_type):
        return

    # Display metrics
    visualizer.display_metrics()
    st.markdown("---")

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
        st.subheader("Competitive Analysis Dashboard")
        visualizer.create_professional_analysis()

    # with tabs[1]:
    #     st.subheader("Website Performance Metrics")
    #     visualizer.create_website_analysis_chart()

    with tabs[1]:
        st.subheader("Simple Topic Comparison")
        visualizer.create_simple_topic_comparison(competitor_type=competitor_type)

    # with tabs[3]:
    #     st.subheader("Topic Distribution & Trends")
    #     visualizer.create_topic_trend_chart(competitor_type=competitor_type)

    with tabs[2]:
        st.subheader("Priority Bubble Matrix")
        visualizer.create_priority_bubble_chart(competitor_type=competitor_type)

    # with tabs[5]:
    #     st.subheader("Topic Trends Timeline")
    #     visualizer.create_trend_timeline(competitor_type=competitor_type)

    # with tabs[6]:
    #     st.subheader("Strategic Competitive Analysis")
    #     visualizer.create_strategic_analysis(competitor_type=competitor_type)

    st.markdown("---")
    
    # Simple insights section
    st.subheader("Summary")
    
    if not visualizer.base_data.empty and not visualizer.competitor_data.empty:
        base_topics = visualizer.extract_topics(visualizer.base_data)
        competitor_topics = visualizer.extract_topics(visualizer.competitor_data)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Your Topics", len(base_topics))
        with col2:
            st.metric("Competitor Topics", len(competitor_topics))
        with col3:
            common_topics = set(base_topics.keys()) & set(competitor_topics.keys())
            st.metric("Common Topics", len(common_topics))
        
        st.markdown("---")
        # st.subheader("Key Findings")
        
        # col1, col2 = st.columns(2)
        # with col1:
        #     st.write("**Your Unique Topics:**")
        #     unique_base = set(base_topics.keys()) - set(competitor_topics.keys())
        #     for topic in list(unique_base)[:5]:
        #         st.write(f"• {topic}")
        
        # with col2:
        #     st.write("**Competitor Unique Topics:**")
        #     unique_comp = set(competitor_topics.keys()) - set(base_topics.keys())
        #     for topic in list(unique_comp)[:5]:
        #         st.write(f"• {topic}")

