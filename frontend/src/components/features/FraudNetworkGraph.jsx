// frontend/src/components/features/FraudNetworkGraph.jsx
import React, { useState, useEffect } from 'react';
import { GitBranch, UserCheck, Phone, CreditCard, ShieldAlert, Award } from 'lucide-react';
import { api } from '../../services/api';

export const FraudNetworkGraph = ({ selectedCluster = null }) => {
  const [networkData, setNetworkData] = useState({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeDetails, setNodeDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [detailsLoading, setDetailsLoading] = useState(false);

  const graphWidth = 450;
  const graphHeight = 350;

  // Retrieve Graph Network on load
  useEffect(() => {
    const fetchNetwork = async () => {
      setLoading(true);
      try {
        const res = await api.getNetwork(selectedCluster);
        
        // Converted Node Positions
        const cx = graphWidth / 2;
        const cy = graphHeight / 2;
        
        const nodesList = res.nodes || [];
        const positionedNodes = nodesList.map((node, index) => {
          let r, theta;
          // Determine ring layout based on entity characteristics
          if (node.isCentral || node.is_central) {
            r = 0; // Mastermind at the dead center
            theta = 0;
          } else if (node.type === 'phone' || node.entity_type === 'phone') {
            r = graphWidth * 0.18; // Phone ring
            theta = (index * 2 * Math.PI) / nodesList.length;
          } else if (node.type === 'account' || node.entity_type === 'account') {
            r = graphWidth * 0.28; // Account ring
            theta = (index * 2 * Math.PI) / nodesList.length + Math.PI / 6;
          } else {
            r = graphWidth * 0.38; // Victims on the outer ring
            theta = (index * 2 * Math.PI) / nodesList.length - Math.PI / 6;
          }

          return {
            ...node,
            x: cx + r * Math.cos(theta),
            y: cy + r * Math.sin(theta),
          };
        });

        setNetworkData({
          nodes: positionedNodes,
          edges: res.edges || []
        });
      } catch (err) {
        console.error('Error fetching network graph:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchNetwork();
  }, [selectedCluster]);

  // Retrieve Node Details on click
  const handleNodeClick = async (node) => {
    setSelectedNode(node);
    setDetailsLoading(true);
    try {
      const details = await api.getNodeDetails(node.id);
      setNodeDetails(details);
    } catch (err) {
      console.error('Error fetching node details:', err);
      // Fallback local details mock
      setNodeDetails({
        entity: node,
        connected_reports: [
          { id: '1', report_type: 'digital_arrest', description: 'Suspect pretended to be CBI Officer Rajesh Kumar, forcing victim to stay on Skype video call.', risk_score: 0.94, created_at: '2026-06-26 12:44:00' }
        ],
        centrality_score: node.isCentral ? 0.84 : 0.12,
        cluster: { name: 'Operation Mamba' }
      });
    } finally {
      setDetailsLoading(false);
    }
  };

  const getNodeColor = (node) => {
    if (node.isCentral || node.is_central) return 'var(--accent-orange)'; // Mastermind Node
    if (node.type === 'phone' || node.entity_type === 'phone') return 'var(--accent-red)';
    if (node.type === 'account' || node.entity_type === 'account') return 'var(--accent-purple)';
    return 'var(--accent-green)'; // Victim
  };

  const getEntityIcon = (type, isCentral) => {
    if (isCentral) return <Award size={14} color="var(--accent-orange)" />;
    if (type === 'phone' || type === 'phone') return <Phone size={14} color="var(--accent-red)" />;
    if (type === 'account' || type === 'account') return <CreditCard size={14} color="var(--accent-purple)" />;
    return <UserCheck size={14} color="var(--accent-green)" />;
  };

  return (
    <div className="glass-panel" style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column', minHeight: '400px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
        <GitBranch size={18} color="var(--accent-cyan)" />
        <h3 style={{ fontSize: '1rem' }}>Coordinated Fraud Network</h3>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '20px', flex: 1, overflow: 'hidden' }}>
        {/* SVG Graph Viewport */}
        <div style={{ background: '#070a12', borderRadius: '12px', border: '1px solid var(--border-glass)', display: 'flex', justifyContent: 'center', alignItems: 'center', position: 'relative' }}>
          {loading ? (
            <div style={{ color: 'var(--text-secondary)' }}>Loading Fraud Links...</div>
          ) : (
            <svg 
              viewBox={`0 0 ${graphWidth} ${graphHeight}`}
              style={{ width: '100%', height: '100%', maxHeight: '300px' }}
            >
              {/* Draw Edges */}
              {networkData.edges.map((edge, idx) => {
                const sourceNode = networkData.nodes.find((n) => n.id === edge.source_id || n.id === edge.source);
                const targetNode = networkData.nodes.find((n) => n.id === edge.target_id || n.id === edge.target);

                if (!sourceNode || !targetNode) return null;

                return (
                  <line
                    key={idx}
                    x1={sourceNode.x}
                    y1={sourceNode.y}
                    x2={targetNode.x}
                    y2={targetNode.y}
                    stroke="rgba(255, 255, 255, 0.08)"
                    strokeWidth={Math.min(4, Math.max(1, edge.weight || 1))}
                  />
                );
              })}

              {/* Draw Nodes */}
              {networkData.nodes.map((node) => {
                const nodeColor = getNodeColor(node);
                const isSelected = selectedNode?.id === node.id;

                return (
                  <g 
                    key={node.id} 
                    transform={`translate(${node.x}, ${node.y})`}
                    onClick={() => handleNodeClick(node)}
                    style={{ cursor: 'pointer' }}
                  >
                    {/* Glowing outer selected boundary */}
                    {isSelected && (
                      <circle r="14" fill="none" stroke="var(--accent-cyan)" strokeWidth="2" className="animate-pulse" />
                    )}

                    {/* Node Core */}
                    <circle
                      r={node.isCentral || node.is_central ? 10 : 8}
                      fill={nodeColor}
                      stroke="rgba(0,0,0,0.4)"
                      strokeWidth="2"
                    />

                    {/* Label */}
                    <text
                      y={node.isCentral || node.is_central ? -14 : -12}
                      textAnchor="middle"
                      fill="var(--text-secondary)"
                      fontSize="9"
                      fontWeight="bold"
                      style={{ pointerEvents: 'none', background: 'rgba(0,0,0,0.8)' }}
                    >
                      {node.label || node.value || node.id}
                    </text>
                  </g>
                );
              })}
            </svg>
          )}
        </div>

        {/* Node Details Inspector */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto' }}>
          {selectedNode ? (
            detailsLoading ? (
              <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                Querying nodes from command ledger...
              </div>
            ) : nodeDetails ? (
              <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {/* Node Identity header */}
                <div style={{ padding: '12px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-glass)', borderRadius: '8px', display: 'flex', gap: '10px', alignItems: 'center' }}>
                  {getEntityIcon(nodeDetails.entity.type || nodeDetails.entity.entity_type, nodeDetails.entity.is_central || nodeDetails.entity.isCentral)}
                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block' }}>
                      {(nodeDetails.entity.type || nodeDetails.entity.entity_type)?.toUpperCase()}
                    </span>
                    <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                      {nodeDetails.entity.value || nodeDetails.entity.id}
                    </strong>
                  </div>
                </div>

                {/* Metrics */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-glass)', padding: '8px', borderRadius: '6px', textAlign: 'center' }}>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', display: 'block' }}>Centrality</span>
                    <strong style={{ fontSize: '0.95rem' }}>{Math.round(nodeDetails.centrality_score * 100)}%</strong>
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-glass)', padding: '8px', borderRadius: '6px', textAlign: 'center' }}>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', display: 'block' }}>Fraud Ring</span>
                    <strong style={{ fontSize: '0.8rem', color: 'var(--accent-orange)' }}>
                      {nodeDetails.cluster ? nodeDetails.cluster.name : 'Unclustered'}
                    </strong>
                  </div>
                </div>

                {/* Linked Reports list */}
                <div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                    Connected Complaints ({nodeDetails.connected_reports.length})
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '150px', overflowY: 'auto' }}>
                    {nodeDetails.connected_reports.map((rep) => (
                      <div key={rep.id} style={{ padding: '8px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-glass)', borderRadius: '6px', fontSize: '0.75rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--accent-red)', fontWeight: '600', marginBottom: '2px' }}>
                          <span>{rep.report_type}</span>
                          <span>Score: {Math.round(rep.risk_score * 100)}%</span>
                        </div>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.7rem', lineHeight: '1.3' }}>
                          {rep.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null
          ) : (
            <div style={{ border: '1px dashed var(--border-glass)', padding: '40px 10px', borderRadius: '8px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
              <ShieldAlert size={20} color="var(--text-muted)" />
              Select any graph entity to inspect relationship metadata
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default FraudNetworkGraph;
