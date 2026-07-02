import React, { useState, useEffect, useRef } from 'react';
import { GitBranch, UserCheck, Phone, CreditCard, ShieldAlert, Award, Search, Download, RefreshCw, Filter } from 'lucide-react';
import { api } from '../../services/api';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';

export const FraudNetworkGraph = ({ selectedCluster = null }) => {
  const [networkData, setNetworkData] = useState({ nodes: [], edges: [] });
  const [clusters, setClusters] = useState([]);
  const [activeCluster, setActiveCluster] = useState(selectedCluster || '');
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeDetails, setNodeDetails] = useState(null);
  
  const [loading, setLoading] = useState(false);
  const [detailsLoading, setDetailsLoading] = useState(false);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [edgeFilters, setEdgeFilters] = useState({ called: true, transacted_with: true });
  const [recomputing, setRecomputing] = useState(false);
  
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState(null);

  const graphWidth = 600;
  const graphHeight = 500;

  // Polling for recompute status
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await api.getRecomputeStatus();
        setRecomputing(res.is_recomputing);
      } catch (e) {
        console.error("Failed to fetch recompute status", e);
      }
    };
    checkStatus();
    const interval = setInterval(checkStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch Clusters
  useEffect(() => {
    const fetchClusters = async () => {
      try {
        const res = await api.getClusters();
        setClusters(res.clusters || []);
      } catch (e) {
        console.error("Failed to fetch clusters", e);
      }
    };
    fetchClusters();
  }, []);

  const runPhysics = (nodes, edges) => {
    const cx = graphWidth / 2;
    const cy = graphHeight / 2;
    let simNodes = nodes.map(n => ({...n, x: cx + (Math.random()-0.5)*100, y: cy + (Math.random()-0.5)*100, vx: 0, vy: 0}));
    
    const ITERATIONS = 120;
    const k = Math.sqrt((graphWidth * graphHeight) / (simNodes.length || 1));
    const repulsion = k * k;
  
    for (let i = 0; i < ITERATIONS; i++) {
      // Repulsion
      for (let a = 0; a < simNodes.length; a++) {
        for (let b = a + 1; b < simNodes.length; b++) {
          let n1 = simNodes[a];
          let n2 = simNodes[b];
          let dx = n1.x - n2.x;
          let dy = n1.y - n2.y;
          let d2 = dx*dx + dy*dy;
          if (d2 > 0 && d2 < 50000) {
            let d = Math.sqrt(d2);
            let force = repulsion / d;
            let fx = (dx / d) * force;
            let fy = (dy / d) * force;
            n1.vx += fx; n1.vy += fy;
            n2.vx -= fx; n2.vy -= fy;
          }
        }
      }
  
      // Attraction
      edges.forEach(e => {
        let n1 = simNodes.find(n => n.id === (e.source || e.source_id));
        let n2 = simNodes.find(n => n.id === (e.target || e.target_id));
        if (n1 && n2) {
          let dx = n1.x - n2.x;
          let dy = n1.y - n2.y;
          let d = Math.sqrt(dx*dx + dy*dy);
          if (d > 0) {
            let force = (d * d) / (k * 0.5); // stronger attraction
            let fx = (dx / d) * force;
            let fy = (dy / d) * force;
            n1.vx -= fx; n1.vy -= fy;
            n2.vx += fx; n2.vy += fy;
          }
        }
      });
  
      // Gravity
      simNodes.forEach(n => {
        let dx = cx - n.x;
        let dy = cy - n.y;
        let d = Math.sqrt(dx*dx + dy*dy);
        if (d > 0) {
          let force = d * 0.05;
          n.vx += (dx / d) * force;
          n.vy += (dy / d) * force;
        }
      });
  
      // Update positions and apply friction
      simNodes.forEach(n => {
        n.vx *= 0.15; // cooling / friction
        n.vy *= 0.15;
        n.x += n.vx;
        n.y += n.vy;
        n.x = Math.max(30, Math.min(graphWidth - 30, n.x));
        n.y = Math.max(30, Math.min(graphHeight - 30, n.y));
      });
    }
    return simNodes;
  };

  // Retrieve Graph Network on load or cluster change
  useEffect(() => {
    const fetchNetwork = async () => {
      setLoading(true);
      try {
        const clusterParam = activeCluster ? parseInt(activeCluster) : null;
        const res = await api.getNetwork(clusterParam, 200);
        
        const nodesList = res.nodes || [];
        const edgesList = res.edges || [];
        
        const positionedNodes = runPhysics(nodesList, edgesList);

        setNetworkData({
          nodes: positionedNodes,
          edges: edgesList
        });
      } finally {
        setLoading(false);
      }
    };

    fetchNetwork();
  }, [activeCluster]);

  const handleNodeClick = async (node) => {
    setSelectedNode(node);
    setDetailsLoading(true);
    try {
      const details = await api.getNodeDetails(node.id);
      setNodeDetails(details);
    } catch (err) {
      setNodeDetails(null);
    } finally {
      setDetailsLoading(false);
    }
  };

  const handleExport = async () => {
    if (!activeCluster) {
        alert("Please select a specific cluster to export.");
        return;
    }
    setExporting(true);
    try {
        const res = await api.startEvidencePackage(activeCluster);
        const taskId = res.task_id;
        
        // Poll for result
        const poll = setInterval(async () => {
            try {
                const statusRes = await api.getEvidencePackageResult(taskId);
                if (statusRes.status === 'complete') {
                    clearInterval(poll);
                    setExporting(false);
                    setExportResult(statusRes.result?.pdf_url || 'Export Complete');
                    alert("Investigation export complete!");
                } else if (statusRes.status === 'failed') {
                    clearInterval(poll);
                    setExporting(false);
                    alert("Export failed: " + statusRes.error);
                }
            } catch (e) {
                // ignore
            }
        }, 3000);
    } catch (e) {
        console.error(e);
        setExporting(false);
        alert("Failed to start export.");
    }
  };

  const getNodeColor = (node) => {
    if (node.isCentral || node.is_central) return 'var(--accent-orange)';
    if (node.type === 'phone' || node.entity_type === 'phone') return 'var(--accent-red)';
    if (node.type === 'account' || node.entity_type === 'account') return 'var(--accent-purple)';
    return 'var(--accent-green)';
  };

  const getEntityIcon = (type, isCentral) => {
    if (isCentral) return <Award size={14} color="var(--accent-orange)" />;
    if (type === 'phone') return <Phone size={14} color="var(--accent-red)" />;
    if (type === 'account') return <CreditCard size={14} color="var(--accent-purple)" />;
    return <UserCheck size={14} color="var(--accent-green)" />;
  };

  return (
    <div className="glass-panel" style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column', minHeight: '500px' }}>
      
      {/* Header Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <GitBranch size={18} color="var(--accent-cyan)" />
          <h3 style={{ fontSize: '1rem', margin: 0 }}>Coordinated Fraud Network</h3>
          {recomputing && (
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--accent-orange)' }}>
              <RefreshCw size={12} className="animate-spin" /> Recomputing...
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', background: 'var(--bg-tertiary)', padding: '4px 8px', borderRadius: '6px', border: '1px solid var(--border-glass)' }}>
                <Search size={14} color="var(--text-muted)" style={{ marginRight: '6px' }} />
                <input 
                    type="text" 
                    placeholder="Search entity..." 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--text-primary)', outline: 'none', fontSize: '0.8rem', width: '120px' }}
                />
            </div>

            <select 
                value={activeCluster} 
                onChange={(e) => setActiveCluster(e.target.value)}
                style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-glass)', color: 'var(--text-primary)', padding: '6px 10px', borderRadius: '6px', fontSize: '0.8rem', outline: 'none' }}
            >
                <option value="">All Clusters</option>
                {clusters.map(c => (
                    <option key={c.id} value={c.id}>{c.name || `Cluster ${c.id}`} ({c.entity_count} entities)</option>
                ))}
            </select>

            <button 
                onClick={handleExport}
                disabled={exporting || !activeCluster}
                className="glass-button"
                style={{ padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem' }}
            >
                {exporting ? <RefreshCw size={14} className="animate-spin" /> : <Download size={14} />}
                Export Investigation
            </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '10px', fontSize: '0.8rem' }}>
          <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}><Filter size={12} /> Edge Filters:</span>
          <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
              <input type="checkbox" checked={edgeFilters.called} onChange={(e) => setEdgeFilters({...edgeFilters, called: e.target.checked})} /> Calls
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
              <input type="checkbox" checked={edgeFilters.transacted_with} onChange={(e) => setEdgeFilters({...edgeFilters, transacted_with: e.target.checked})} /> Transactions
          </label>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '20px', flex: 1, overflow: 'hidden' }}>
        {/* SVG Graph Viewport */}
        <div style={{ background: '#070a12', borderRadius: '12px', border: '1px solid var(--border-glass)', display: 'flex', justifyContent: 'center', alignItems: 'center', position: 'relative' }}>
          {loading ? (
            <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: 'var(--accent-cyan)' }}>
              Calculating physics layout...
            </div>
          ) : (
            <TransformWrapper initialScale={1} minScale={0.5} maxScale={4}>
              <TransformComponent wrapperStyle={{ width: '100%', height: '100%' }}>
                <svg viewBox={`0 0 ${graphWidth} ${graphHeight}`} style={{ width: '100%', height: '100%' }}>
                  {/* Edges */}
                  {networkData.edges.map((edge, i) => {
                    const relType = edge.relationship || 'unknown';
                    if (relType === 'called' && !edgeFilters.called) return null;
                    if (relType === 'transacted_with' && !edgeFilters.transacted_with) return null;

                    const sourceNode = networkData.nodes.find((n) => n.id === (edge.source || edge.source_id));
                    const targetNode = networkData.nodes.find((n) => n.id === (edge.target || edge.target_id));
                    if (!sourceNode || !targetNode) return null;
                    
                    const midX = (sourceNode.x + targetNode.x) / 2;
                    const midY = (sourceNode.y + targetNode.y) / 2;

                    return (
                      <g key={`edge-${i}`}>
                        <line
                            x1={sourceNode.x}
                            y1={sourceNode.y}
                            x2={targetNode.x}
                            y2={targetNode.y}
                            stroke={relType === 'called' ? 'var(--accent-cyan)' : 'var(--accent-purple)'}
                            strokeWidth={(edge.weight || 1) * 0.5}
                            opacity="0.3"
                        />
                        <text
                            x={midX}
                            y={midY}
                            fill="var(--text-muted)"
                            fontSize="6"
                            textAnchor="middle"
                            opacity="0.6"
                            style={{ pointerEvents: 'none' }}
                        >
                            {relType}
                        </text>
                      </g>
                    );
                  })}

                  {/* Nodes */}
                  {networkData.nodes.map((node) => {
                    const isSelected = selectedNode?.id === node.id;
                    const nodeColor = getNodeColor(node);
                    const rawLabel = node.label || node.value || node.id;
                    const isSearchMatch = searchQuery && rawLabel.toLowerCase().includes(searchQuery.toLowerCase());

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
                        {isSearchMatch && (
                          <circle r="16" fill="none" stroke="yellow" strokeWidth="2" className="animate-pulse" />
                        )}

                        {/* Node Core */}
                        <circle
                          r={node.isCentral || node.is_central ? 10 : 8}
                          fill={nodeColor}
                          stroke="rgba(0,0,0,0.4)"
                          strokeWidth="2"
                        >
                          <title>{rawLabel}</title>
                        </circle>

                        {/* Label */}
                        <text
                          y={node.isCentral || node.is_central ? -14 : -12}
                          textAnchor="middle"
                          fill={isSearchMatch ? "yellow" : "var(--text-secondary)"}
                          fontSize="9"
                          fontWeight={isSearchMatch ? "bold" : "normal"}
                          style={{ pointerEvents: 'none', background: 'rgba(0,0,0,0.8)' }}
                        >
                          {(() => {
                            if (typeof rawLabel === 'string' && rawLabel.length > 15) {
                              return rawLabel.substring(0, 15) + '...';
                            }
                            return rawLabel;
                          })()}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </TransformComponent>
            </TransformWrapper>
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
                    <strong style={{ fontSize: '0.95rem' }}>{Math.round((nodeDetails.centrality_score || 0) * 100)}%</strong>
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-glass)', padding: '8px', borderRadius: '6px', textAlign: 'center' }}>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', display: 'block' }}>Fraud Ring</span>
                    <strong style={{ fontSize: '0.8rem', color: 'var(--accent-orange)' }}>
                      {nodeDetails.cluster ? (nodeDetails.cluster.name || `Cluster ${nodeDetails.cluster.id}`) : 'Unclustered'}
                    </strong>
                  </div>
                </div>

                {/* Linked Reports list */}
                <div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                    Connected Complaints ({nodeDetails.connected_reports?.length || 0})
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '150px', overflowY: 'auto' }}>
                    {(nodeDetails.connected_reports || []).map((rep) => (
                      <div key={rep.id} style={{ padding: '8px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-glass)', borderRadius: '6px', fontSize: '0.75rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--accent-red)', fontWeight: '600', marginBottom: '2px' }}>
                          <span>{rep.report_type}</span>
                          <span>Score: {Math.round((rep.risk_score || 0) * 100)}%</span>
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
